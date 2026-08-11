// ══════════════════════════════════════════════════════════════════
// soil.rs — 土壤层 (多层 N/P/K/有机质/pH/水分/温度/微生物)
// ══════════════════════════════════════════════════════════════════
//
// 关键生物地球化学:
//   · 有机质矿化      dN/dt = -k_N·T·θ·C_org   (微生物把有机 N → 铵态 N)
//   · 硝化            NH4 → NO3 (需氧, k_nit·T·θ)
//   · 反硝化          NO3 → N2 (厌氧, 在水分饱和时)
//   · 固持作用       微生物把无机 N 锁住 (C:N >~ 30 触发)
//   · 淋溶          水分通量把 NO3 带到深层
//   · 蒸散           植被蒸腾蒸发把水带走
//
// 单位: 元素 kg/ha (简化, 假设 1 ha × 0.3 m 土层 ≈ 4.5e6 kg 土)
// 土壤水分: m³/m³ (体积含水量 0..1, 田间持水率 fc ≈ 0.35)

use super::atmosphere::Atmosphere;
use super::plant::Plant;

/// 土壤单层 (可叠为多层剖面)
#[derive(Clone, Debug)]
pub struct SoilLayer {
    pub depth_m: f64,           // 层深度 (顶部到底部, m)
    /// 元素库 (kg/ha)
    pub n_no3: f64,             // 硝态氮 (速效)
    pub n_nh4: f64,             // 铵态氮 (速效)
    pub n_org: f64,             // 有机氮 (缓效)
    pub p_labile: f64,          // 速效磷
    pub p_org: f64,             // 有机磷
    pub k_exchange: f64,        // 交换性钾
    pub c_org: f64,             // 有机碳 (g/kg → kg/ha)
    /// 物理
    pub water_pct: f64,         // 体积含水量 m³/m³ (0..1)
    pub field_capacity: f64,    // 田间持水率
    pub wilting_point: f64,     // 萎蔫点
    pub ph: f64,
    pub microbial_biomass: f64, // kg C / ha
    /// 温度 (℃) — 比气温相位滞后
    pub temp_c: f64,
}

impl SoilLayer {
    pub fn new(depth_top_m: f64, depth_bottom_m: f64) -> Self {
        let thickness = depth_bottom_m - depth_top_m;
        Self {
            depth_m: thickness,
            n_no3:  18.0,
            n_nh4:   6.0,
            n_org: 40.0,
            p_labile: 5.0,
            p_org: 10.0,
            k_exchange: 30.0,
            c_org: 12_000.0,             // 约 1.2% 有机碳
            water_pct: 0.30,
            field_capacity: 0.32,
            wilting_point: 0.05,
            ph: 6.5,
            microbial_biomass: 60.0,
            temp_c: 18.0,
        }
    }

    /// 速效 N (植物可吸收)
    #[inline]
    pub fn n_available(&self) -> f64 { self.n_no3 + self.n_nh4 }

    /// 有效水分应力 0..1 (1=无应力)
    pub fn water_stress(&self) -> f64 {
        if self.water_pct >= self.field_capacity { return 1.0; }
        if self.water_pct <= self.wilting_point { return 0.0; }
        (self.water_pct - self.wilting_point)
            / (self.field_capacity - self.wilting_point)
    }

    /// pH 对养分有效性的折减 (U形, 最适 6.0-7.0)
    pub fn ph_factor(&self) -> f64 {
        let d = (self.ph - 6.5).abs();
        (-d * d / 4.0).exp().min(1.0)
    }

    /// 水分作为微生物活性的函数 (S型)
    pub fn moisture_factor(&self) -> f64 {
        // θ_opt ≈ 0.25..0.30
        let r = self.water_pct / 0.28;
        if r < 1.0 { r * r } else { 1.0 - (r - 1.0) * (r - 1.0) * 0.6 }
    }

    /// 温度 Q10 因子 (基准 20℃)
    pub fn temp_factor(&self) -> f64 {
        let q10 = 2.0_f64;
        q10.powf((self.temp_c - 20.0) / 10.0)
    }

    /// 每天土壤生物地球化学 (简化 Century 模型风格)
    pub fn biogeochemistry_tick(&mut self) {
        let tf = self.temp_factor();
        let mf = self.moisture_factor();
        let ph = self.ph_factor();

        // 1. 有机质矿化 → NH4
        let decay_rate = 0.0008 * tf * mf;
        let dn = self.c_org * decay_rate * 0.05;  // 5% 有机 C 含 N
        if dn > self.c_org * 0.01 { return; }     // 限幅
        self.c_org -= dn * 20.0;                   // C:N 取 20:1
        self.n_nh4 += dn * ph;

        // 2. 微生物固持 (高 C:N 锁定无机 N)
        let cn_ratio = if self.n_org + self.n_available() > 0.0 {
            self.c_org / (self.n_org + self.n_available())
        } else { 0.0 };
        if cn_ratio > 30.0 {
            let n_immob = self.n_available() * 0.1 * tf;
            let take_nh4 = n_immob.min(self.n_nh4);
            self.n_nh4 -= take_nh4;
            let take_no3 = (n_immob - take_nh4).min(self.n_no3);
            self.n_no3 -= take_no3;
            self.n_org += n_immob * 0.7;   // 微生物死亡再释放一部分
            self.c_org += n_immob * 6.0;   // 微生物体 C:N ~ 6
        }

        // 3. 硝化 (需氧水分适中时)
        if self.water_pct < 0.30 && self.water_pct > 0.05 {
            let nit = self.n_nh4 * 0.15 * tf * mf;
            self.n_nh4 -= nit;
            self.n_no3 += nit;
            // 硝化产酸
            self.ph -= nit * 0.002;
        }

        // 4. 反硝化 (厌氧)
        if self.water_pct > self.field_capacity * 0.95 {
            let denit = self.n_no3 * 0.05 * tf;
            self.n_no3 -= denit;
            // 反硝化产碱 (轻微)
            self.ph += denit * 0.0005;
        }

        // 5. 淋溶 (NO3 随重力水流失)
        if self.water_pct > self.field_capacity {
            let drainage = (self.water_pct - self.field_capacity) * 0.5; // 重力排水 m
            let leached = self.n_no3 * drainage * 0.1;
            self.n_no3 -= leached;
        }

        // 6. 有机 N → 有机 C 再平衡
        self.ph = self.ph.clamp(3.5, 9.0);
        self.c_org = self.c_org.max(100.0);
    }

    /// 水分平衡 (输入 mm 降水 + 潜在蒸散发 mm)
    pub fn water_balance(&mut self, rain_mm: f64, et_mm: f64, uptake_by_roots_mm: f64) {
        let thickness_m = self.depth_m;
        // 1 m 土层 1 mm 水 = 0.001 m³/m³ 增水
        let dz = (rain_mm - et_mm - uptake_by_roots_mm).max(-thickness_m * 1000.0) / 1000.0;
        self.water_pct += dz / thickness_m;
        // 排水 (超过田间持水)
        if self.water_pct > self.field_capacity {
            self.water_pct -= (self.water_pct - self.field_capacity) * 0.4;
        }
        self.water_pct = self.water_pct.clamp(0.0, 0.5);
    }

    // ── hash material (用于快照 hash) ──
    pub fn hash_material(&self) -> Vec<u8> {
        let mut v = Vec::new();
        v.extend_from_slice(&self.depth_m.to_be_bytes());
        v.extend_from_slice(&self.n_no3.to_be_bytes());
        v.extend_from_slice(&self.n_nh4.to_be_bytes());
        v.extend_from_slice(&self.p_labile.to_be_bytes());
        v.extend_from_slice(&self.k_exchange.to_be_bytes());
        v.extend_from_slice(&self.c_org.to_be_bytes());
        v.extend_from_slice(&self.water_pct.to_be_bytes());
        v.extend_from_slice(&self.ph.to_be_bytes());
        v.extend_from_slice(&self.temp_c.to_be_bytes());
        v
    }
}

/// 土壤剖面 (多层叠加)
#[derive(Clone, Debug)]
pub struct Soil {
    pub layers: Vec<SoilLayer>,
}

impl Soil {
    pub fn new(_seed: u64) -> Self {
        // 三层: 表土(0-30cm), 心土(30-80cm), 底土(80-200cm)
        Self {
            layers: vec![
                SoilLayer::new(0.0, 0.30),
                SoilLayer::new(0.30, 0.80),
                SoilLayer::new(0.80, 2.00),
            ],
        }
    }

    pub fn top(&self) -> &SoilLayer { &self.layers[0] }
    pub fn top_mut(&mut self) -> &mut SoilLayer { &mut self.layers[0] }

    /// 表层 30cm 总体速效 N (kg/ha)
    #[inline]
    pub fn surface_n(&self) -> f64 { self.layers[0].n_available() }

    #[inline]
    pub fn surface_p(&self) -> f64 { self.layers[0].p_labile }

    #[inline]
    pub fn surface_k(&self) -> f64 { self.layers[0].k_exchange }

    #[inline]
    pub fn surface_water_pct(&self) -> f64 { self.layers[0].water_pct }

    #[inline]
    pub fn ph(&self) -> f64 { self.layers[0].ph }

    /// 推进一日土壤层 (含所有层生物地球化学 + 土壤温度 ← 大气温度滞后)
    pub fn tick(&mut self, atm: &Atmosphere, plants: &mut [Plant], par: f64) {
        // 地表层气温 → 土温滞后 (阻尼 + 相位)
        let damping = 0.4;
        self.layers[0].temp_c = self.layers[0].temp_c * (1.0 - damping) + atm.air_temp_c * damping;
        // 深层温度更稳
        for i in 1..self.layers.len() {
            let above = &self.layers[i - 1].temp_c;
            self.layers[i].temp_c = self.layers[i].temp_c * 0.95 + above * 0.05;
        }

        // 植物根系吸水 (表层)
        let total_uptake: f64 = plants.iter().map(|p| p.water_uptake_mm()).sum();
        let et = atm.potential_et_mm;

        // 表层水分平衡
        self.layers[0].water_balance(atm.rainfall_mm, et * 0.7, total_uptake);

        // 淋溶往下层输水
        if self.layers[0].water_pct > self.layers[0].field_capacity {
            let excess = (self.layers[0].water_pct - self.layers[0].field_capacity) * 0.4;
            self.layers[0].water_pct -= excess;
            if self.layers.len() > 1 {
                self.layers[1].water_pct += excess * 0.5 / self.layers[1].depth_m;
                self.layers[1].water_pct = self.layers[1].water_pct.clamp(0.0, 0.45);
            }
        }

        // 深层较少蒸发
        for i in 1..self.layers.len() {
            let net = -(et * 0.15) / self.layers[i].depth_m;
            self.layers[i].water_pct = (self.layers[i].water_pct + net / 1000.0).clamp(0.0, 0.5);
        }

        // 各层生物地球化学
        for layer in self.layers.iter_mut() {
            layer.biogeochemistry_tick();
        }

        // 钾随植物吸收略有下降 (简化)
        let k_uptake: f64 = plants.iter().map(|p| p.k_uptake_units()).sum();
        self.layers[0].k_exchange = (self.layers[0].k_exchange - k_uptake).max(1.0);

        // 施肥一次性补充 (通过外部函数, 这里不设)
        let _c = par; // 防止 unused 提示
    }

    pub fn hash_material(&self) -> Vec<u8> {
        let mut v = Vec::new();
        for l in &self.layers { v.extend(&l.hash_material()); }
        v
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn layer_nutrient_pools_positive() {
        let l = SoilLayer::new(0.0, 0.3);
        assert!(l.n_available() > 0.0);
        assert!(l.p_labile > 0.0);
        assert!(l.k_exchange > 0.0);
    }

    #[test]
    fn water_balance_increases_with_rain() {
        let mut l = SoilLayer::new(0.0, 0.3);
        let before = l.water_pct;
        l.water_balance(25.0, 3.0, 5.0);
        assert!(l.water_pct > before, "rain should increase water");
    }

    #[test]
    fn soil_layer_bge() {
        let mut l = SoilLayer::new(0.0, 0.3);
        l.temp_c = 30.0;
        l.water_pct = 0.25;
        for _ in 0..30 { l.biogeochemistry_tick(); }
        // N 库不应变负
        assert!(l.n_no3 >= 0.0 && l.n_nh4 >= 0.0);
    }
}
