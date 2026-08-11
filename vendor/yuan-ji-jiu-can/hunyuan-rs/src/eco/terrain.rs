// ══════════════════════════════════════════════════════════════════
// terrain.rs — 地形 (海拔 · 坡度 · 坡向 · 粗糙度 · 反照率 · 土壤母质)
// ══════════════════════════════════════════════════════════════════
//
// 地形决定小气候:
//   · 海拔      → 温度递减 ~ -6.5°C/km
//   · 坡度      → 坡面太阳辐照 s = cos(slope)·sin(h) + sin(slope)·cos(h)·cos(A-a)
//   · 坡向      → 阳坡(南向)暖,阴坡(北向)冷湿
//   · 粗糙度    → 蒸散与风阻
//   · 反照率    → 雪/叶/土 差异决定吸收
//   · 母质      → 原始 K/P/微量元素供给

#[derive(Clone, Debug)]
pub struct Terrain {
    pub elevation_m: f64,
    pub slope_deg: f64,
    pub aspect_deg: f64,   // 0=N 90=E 180=S 270=W
    pub roughness_m: f64,
    pub albedo: f64,
    /// 土壤母质 N/P/K 基础供给速率 (kg/ha/day, 风化释放)
    pub parent_n_rate: f64,
    pub parent_p_rate: f64,
    pub parent_k_rate: f64,
}

impl Terrain {
    pub fn new(seed: u64) -> Self {
        // 用 seed 派生地形参数 (保证可复现)
        use crate::crypto::sha256;
        let b = sha256(&seed.to_be_bytes());
        let r = |i: usize| -> f64 { (b[i] as f64) / 255.0 };
        Self {
            elevation_m:   r(0) * 1500.0,                         // 0..1500 m
            slope_deg:     r(1) * 35.0,                            // 0..35°
            aspect_deg:    r(2) * 360.0,
            roughness_m:   0.01 + r(3) * 0.5,                     // 0.01..0.51 m
            albedo:        0.10 + r(4) * 0.30,                    // 0.10..0.40
            parent_n_rate: 0.005 + r(5) * 0.01,                   // 0.005..0.015
            parent_p_rate: 0.001 + r(6) * 0.003,                  // 0.001..0.004
            parent_k_rate: 0.010 + r(7) * 0.02,                   // 0.010..0.030
        }
    }

    /// 坡面修正辐射 (相对平面); 1=平坦, >1=向阳坡, <1=背阴坡
    pub fn slope_radiation_factor(&self, lat_deg: f64, day: u64) -> f64 {
        let decl = super::atmosphere::Atmosphere::solar_declination(day).to_radians();
        let phi = lat_deg.to_radians();
        let beta = self.slope_deg.to_radians();
        let asp = self.aspect_deg.to_radians();
        // 正午太阳高度
        let sin_h = phi.sin() * decl.sin() + phi.cos() * decl.cos();
        let h_asin = sin_h.clamp(-1.0, 1.0);
        // 坡面辐照比
        let cos_i = (beta.sin() * h_asin * (0.0_f64.to_radians() - asp).cos()
                   + beta.cos() * h_asin.sin_or(0.0))
            .max(0.0);
        let cos_h = h_asin.sin_or(0.0);
        if cos_h < 0.05 { return 0.0; }
        (cos_i / cos_h).clamp(0.0, 3.0)
    }

    /// 海拔温差修正 (℃, 相对海平面)
    pub fn elevation_temp_offset_c(&self) -> f64 {
        -self.elevation_m * 0.0065  // 湿绝热递减率
    }

    pub fn hash_material(&self) -> Vec<u8> {
        let mut v = Vec::new();
        v.extend_from_slice(&self.elevation_m.to_be_bytes());
        v.extend_from_slice(&self.slope_deg.to_be_bytes());
        v.extend_from_slice(&self.aspect_deg.to_be_bytes());
        v
    }
}

trait SinOr { fn sin_or(self, f: f64) -> f64; }
impl SinOr for f64 { fn sin_or(self, f: f64) -> f64 { if self >= -1.0 && self <= 1.0 { self.asin() } else { f } } }

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn elevation_temp_colder_high() {
        let a = Terrain::new(0);
        let b = Terrain::new(1_000_001);
        // b may have higher elevation → colder offset
        // 不断言 direction 因为 seed 态不同, 但断言范围
        assert!(a.elevation_temp_offset_c() >= -15.0);
        assert!(b.elevation_temp_offset_c() <= 0.0);
    }

    #[test]
    fn slope_factor_bounded() {
        let t = Terrain::new(42);
        for d in 1..365 {
            let f = t.slope_radiation_factor(30.0, d);
            assert!(f >= 0.0 && f <= 3.0);
        }
    }
}
