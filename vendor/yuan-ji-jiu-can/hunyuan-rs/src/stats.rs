// ══════════════════════════════════════════════════════════════════
// stats.rs — 统计锥 (Statistical Cone)
// ══════════════════════════════════════════════════════════════════
//
// 统计锥 = 数据统计沿"层级"聚合, 形成锥状:
////   底层 (细粒度) → 中层 (时间窗口) → 顶层 (全局)
//
// 每个锥是一个 (count, mean, min, max, M2) 五元组, 支持
// 在线单遍计算 stddev (Welford)。
//
// 三个锥:
//   1. StreamStats   — 无限流式统计 (内存 O(1))
//   2. Histogram     — 分桶直方图 (可设任意 bucket 边界)
//   3. TimeWindowStats — 滑动时间窗口统计 (按 ms 周期聚合)
//
// 与 holo3d 结合: 统计三维空间的分布密度
// 与 log_ring 结合: 日志事件频率统计

use std::collections::BTreeMap;

/// 在线统计 (Welford, O(1) memory)
#[derive(Clone, Copy, Debug, Default)]
pub struct StreamStats {
    pub count: u64,
    pub mean: f64,
    pub min: f64,
    pub max: f64,
    m2: f64,           // Σ (x-mean)² 累加 (用于 stddem)
}

impl StreamStats {
    pub fn new() -> Self { Self::default() }

    pub fn push(&mut self, x: f64) {
        self.count += 1;
        if self.count == 1 {
            self.mean = x; self.min = x; self.max = x; self.m2 = 0.0;
            return;
        }
        if x < self.min { self.min = x; }
        if x > self.max { self.max = x; }
        // Welford 在线
        let delta = x - self.mean;
        self.mean += delta / self.count as f64;
        let delta2 = x - self.mean;
        self.m2 += delta * delta2;
    }

    pub fn variance(&self) -> f64 {
        if self.count < 2 { 0.0 } else { self.m2 / (self.count - 1) as f64 }
    }

    pub fn stddev(&self) -> f64 { self.variance().sqrt() }

    /// 合并两个统计 (在线并行合并)
    pub fn merge(&self, other: &Self) -> Self {
        if other.count == 0 { return *self; }
        if self.count == 0 { return *other; }
        let n = self.count + other.count;
        let delta = other.mean - self.mean;
        let mean = self.mean + delta * (other.count as f64 / n as f64);
        let m2 = self.m2 + other.m2 + delta * delta
                 * (self.count as f64 * other.count as f64 / n as f64);
        Self {
            count: n,
            mean,
            min: self.min.min(other.min),
            max: self.max.max(other.max),
            m2,
        }
    }
}

/// 直方图 (bucket 边界在构造时确定)
#[derive(Clone, Debug)]
pub struct Histogram {
    pub buckets: Vec<(f64, f64, u64)>, // (lo, hi_exclusive, count)
    pub total: u64,
}

impl Histogram {
    /// 等宽直方图: 把 [min,max] 切成 n_bucket 个等宽桶
    pub fn uniform(n_bucket: usize, lo: f64, hi: f64) -> Self {
        assert!(n_bucket > 0 && hi > lo);
        let width = (hi - lo) / n_bucket as f64;
        let mut b = Vec::with_capacity(n_bucket);
        for i in 0..n_bucket {
            let a = lo + width * i as f64;
            let z = if i == n_bucket-1 { hi } else { a + width };
            b.push((a, z, 0));
        }
        Self { buckets: b, total: 0 }
    }

    pub fn push(&mut self, x: f64) {
        self.total += 1;
        for b in &mut self.buckets {
            if x >= b.0 && x < b.1 { b.2 += 1; return; }
        }
        // 右边界外的归入最后一个桶
        if x >= self.buckets[self.buckets.len()-1].1 {
            self.buckets.last_mut().unwrap().2 += 1;
        }
    }

    /// 概率密度 = 该桶 count / total / width
    pub fn density(&self, i: usize) -> Option<f64> {
        self.buckets.get(i).map(|(lo, hi, c)| {
            if self.total == 0 || hi <= lo { return 0.0; }
            *c as f64 / self.total as f64 / (hi - lo)
        })
    }
}

/// 滑动时间窗口统计: 按秒/分/时 三层统计
#[derive(Clone, Debug)]
pub struct TimeWindowStats {
    /// granularity_ms 窗口 (底层) 计 count
    pub window_ms: u64,
    /// 每窗口 BTreeMap<window_id, count>
    pub windows: BTreeMap<u64, u64>,
    pub total: u64,
}

impl TimeWindowStats {
    pub fn new(window_ms: u64) -> Self {
        assert!(window_ms > 0);
        Self { window_ms, windows: BTreeMap::new(), total: 0 }
    }

    /// 在 ts_ms 处发生一次事件
    pub fn hit(&mut self, ts_ms: u64) {
        let wid = ts_ms / self.window_ms;
        *self.windows.entry(wid).or_insert(0) += 1;
        self.total += 1;
    }

    /// 清理窗口编号 < wid 的 (限内存)
    pub fn trim_before(&mut self, wid: u64) {
        self.windows = self.windows.split_off(&wid);
    }

    /// 速率 (events / window_ms seconds)
    pub fn rate_per_sec(&self) -> f64 {
        if self.windows.is_empty() { return 0.0; }
        let total: u64 = self.windows.values().sum();
        total as f64 / (self.windows.len() as f64 * self.window_ms as f64 / 1000.0)
    }

    #[inline]
    pub fn unique_windows(&self) -> usize { self.windows.len() }
}

/// 三维密度分析: 把 xyz 坐标落到 n×n×n 网格, 统计每个格子的点数
#[derive(Clone, Debug)]
pub struct SpaceDensity {
    pub n: u32,
    pub cells: Vec<u32>,
}

impl SpaceDensity {
    pub fn new(n: u32) -> Self {
        let n3 = (n as usize).pow(3);
        Self { n, cells: vec![0; n3] }
    }

    fn idx(&self, x: u32, y: u32, z: u32) -> usize {
        (x as usize) + (y as usize) * (self.n as usize)
                   + (z as usize) * (self.n as usize).pow(2)
    }

    /// 加入一个 [0..255]³ 中的点
    pub fn push(&mut self, x: u8, y: u8, z: u8) {
        let n = self.n as u32;
        let xi = (x as u32 * n / 256).min(n - 1);
        let yi = (y as u32 * n / 256).min(n - 1);
        let zi = (z as u32 * n / 256).min(n - 1);
        let i = self.idx(xi, yi, zi);
        self.cells[i] += 1;
    }

    pub fn total(&self) -> u64 {
        self.cells.iter().map(|&c| c as u64).sum()
    }

    /// 信息熵 (bits) — 空间分布不均匀度
    pub fn entropy_bits(&self) -> f64 {
        let total = self.total() as f64;
        if total == 0.0 { return 0.0; }
        let mut h = 0.0_f64;
        for &c in &self.cells {
            if c == 0 { continue; }
            let p = c as f64 / total;
            h -= p * p.ln();
        }
        h / std::f64::consts::LN_2  // 转成 bits
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn welford_basic() {
        let mut s = StreamStats::new();
        for x in 1..=5 { s.push(x as f64); }
        assert_eq!(s.count, 5);
        assert!((s.mean - 3.0).abs() < 1e-9);
        assert!((s.stddev() - 1.581138).abs() < 1e-5);
    }

    #[test]
    fn hist_uniform() {
        let mut h = Histogram::uniform(10, 0.0, 10.0);
        for x in 0..10 { h.push(x as f64); }
        assert_eq!(h.total, 10);
        assert_eq!(h.buckets[0].2, 1);
    }

    #[test]
    fn tws_rate() {
        let mut tws = TimeWindowStats::new(1000); // 1s
        for _ in 0..10 { tws.hit(100); }   // window 0
        for _ in 0..5  { tws.hit(1500); }  // window 1
        assert_eq!(tws.total, 15);
        // 15 events / 2s window span = 7.5/sec average across window
        assert!((tws.rate_per_sec() - 7.5).abs() < 0.5);
    }

    #[test]
    fn space_density_entropy() {
        let mut d = SpaceDensity::new(4);
        for _ in 0..100 { d.push(10, 10, 10); } // 全集中一点
        assert!(d.entropy_bits() < 0.1, "concentrated → 低熵");
    }

    #[test]
    fn stream_merge() {
        let mut a = StreamStats::new();
        for x in 1..=3 { a.push(x as f64); }
        let mut b = StreamStats::new();
        for x in 4..=6 { b.push(x as f64); }
        let m = a.merge(&b);
        assert_eq!(m.count, 6);
        assert!((m.mean - 3.5).abs() < 1e-9);
    }
}
