// ══════════════════════════════════════════════════════════════════
// mod.rs — 满全法 · 活生态系统总控 (eco)
// ══════════════════════════════════════════════════════════════════
//
// 这是满全法里"统计锥"的真正肉身。统计锥不再只是均值/方差计数器,
// 而是对一个活生态系统的逐日追踪与统计。
//
// 模块组成 (自下而上):
//
//   层        模块            物理量                       ┐
//   ──────────────────────────────────────────────────────┤
//   土壤       soil.rs        N/P/K 有机质 水分 pH 温度   │
//   大气       atmosphere.rs  温度 云 降雨 风 日照时数     │
//   地形       terrain.rs     海拔 坡度 坡向 粗糙度        │
//   物候       phonology.rs   积温 光周期 生育期           │ 森林
//   个体       plant.rs       根/茎/叶/花/果/生物量         │
//   种群       population.rs  多株竞争/互惠/遗传漂变        │
//   群落       community.rs   林冠层次 光竞争 水分竞争      │
//   气候       climate.rs     年际 ENSO 振动                │
//   统计       stats.rs       对所有层的抽样 + 趋势 + 异常   │
//                                                              ┘
//
// 整个系统按"日"推进:
//   eco.tick(day)  →  [气候] → [大气] → [土壤] → [物候] → [个体]
//                  →  [种群] → [群落] → [统计采样]
//
// 关键方程 (简化真实物理):
//   · 气温    T = T_mean + A·sin(2π·d/365) + noise
//   · 降雨    Bernoulli(p_season), 强度 Gamma(shape=S, rate=r)
//   · 土壤水分 dW/dt = 降雨 + 灌溉 - 蒸散 - 深层渗漏
//   · 植被生物量 dB/dt = ε·PAR·f(W)·f(T)·f(N) - 呼吸 - 落叶
//   · PAR      = f(太阳高度角, 云量, 叶面积指数 LAI)

pub mod soil;
pub mod atmosphere;
pub mod terrain;
pub mod plant;
pub mod stats;

pub use soil::*;
pub use atmosphere::*;
pub use terrain::*;
pub use plant::*;
pub use stats::*;

use crate::crypto::sha256;

/// 生态系统的完整状态 (可作为 consciousness snapshot)
#[derive(Clone, Debug)]
pub struct Ecosystem {
    pub day: u64,
    pub soil: soil::Soil,
    pub atm: atmosphere::Atmosphere,
    pub terrain: terrain::Terrain,
    pub plants: Vec<plant::Plant>,
    pub stats_daily: Vec<stats::DailyStats>,
    pub position_lat: f64,   // 纬度 (影响日照角)
    pub seed: u64,
}

impl Ecosystem {
    pub fn new(lat_deg: f64, seed: u64) -> Self {
        Self {
            day: 0,
            soil: soil::Soil::new(seed),
            atm: atmosphere::Atmosphere::new(lat_deg),
            terrain: terrain::Terrain::new(seed),
            plants: Vec::new(),
            stats_daily: Vec::new(),
            position_lat: lat_deg,
            seed,
        }
    }

    /// 种一棵植物
    pub fn plant(&mut self, kind: plant::PlantKind, age_days: u64) {
        self.plants.push(plant::Plant::new(kind, age_days));
    }

    /// 推进一日
    pub fn tick(&mut self) -> &stats::DailyStats {
        // 1: 大气
        self.atm.tick(self.day);
        // 2: 阳光 / 叶面积衰减辐射穿透
        let lai = self.plants.iter().map(|p| p.leaf_area_index()).sum::<f64>();
        let par = self.atm.par_after_canopy(lai);
        // 3: 土壤 ← 降雨 + 根系吸水
        self.soil.tick(&self.atm, &mut self.plants, par);
        // 4: 植株逐日生长
        for p in &mut self.plants {
            p.tick(&self.atm, &self.soil, par);
        }
        // 5: 统计
        let sample = stats::DailyStats::sample(
            self.day, &self.atm, &self.soil, &self.plants, par, lai,
        );
        self.stats_daily.push(sample.clone());
        self.day += 1;
        self.stats_daily.last().unwrap()
    }

    /// 摘要一行 (供 demo 用)
    pub fn summary(&self) -> String {
        let s = self.stats_daily.last();
        match s {
            Some(s) => format!(
                "day {:>3} T={:>5.1}C rain={:>4.1}mm soilH2O={:>5.1}% N={:>4.1} P={:>4.1} K={:>4.1} LAI={:.2} fruits={} biomass={:.1}g",
                s.day, s.air_temp_c, s.rainfall_mm, s.soil_moisture_pct,
                s.soil_n, s.soil_p, s.soil_k, s.lai, s.fruit_count, s.total_biomass_g,
            ),
            None => "(empty)".into(),
        }
    }
}

/// "意识快照" = 当前状态哈希 (可用于跨节点同步 / 防篡改)
pub fn snapshot_hash(eco: &Ecosystem) -> [u8; 32] {
    let mut buf = Vec::with_capacity(8 * 16);
    buf.extend_from_slice(&eco.day.to_be_bytes());
    buf.extend_from_slice(&eco.seed.to_be_bytes());
    buf.extend(&eco.atm.hash_material());
    buf.extend(&eco.soil.hash_material());
    for p in &eco.plants { buf.extend(&p.hash_material()); }
    sha256(&buf)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ecosystem_spinup() {
        let mut eco = Ecosystem::new(30.0, 0xC0FFEE);
        eco.plant(plant::PlantKind::Woody { name: "测试树".into() }, 0);
        for _ in 0..365 { eco.tick(); }
        assert_eq!(eco.day, 365);
        assert!(eco.stats_daily.len() == 365);
        // 植株应生长
        assert!(eco.plants[0].biomass_g() > 0.0);
    }

    #[test]
    fn hash_changes_per_day() {
        let mut eco = Ecosystem::new(30.0, 123);
        let h1 = snapshot_hash(&eco);
        eco.tick();
        eco.tick();
        let h2 = snapshot_hash(&eco);
        assert_ne!(h1, h2);
    }
}
