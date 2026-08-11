// ══════════════════════════════════════════════════════════════════
// stats.rs — 锥状统计 (多层采样 + 趋势 + 异常)
// ══════════════════════════════════════════════════════════════════
//
// No longer a hollow cone: samples the LIVE ecosystem every day
// and provides running min/mean/max/stddev per-channel over the history,
// plus DEMA (double exponential moving average) for trend,
// plus anomaly detection = |x - μ| > 3σ on that channel.

use crate::eco::atmosphere::Atmosphere;
use crate::eco::soil::Soil;
use crate::eco::plant::Plant;

/// 每日采样 (31 字段)
#[derive(Clone, Debug)]
pub struct DailyStats {
    pub day: u64,
    pub air_temp_c: f64,
    pub rainfall_mm: f64,
    pub par_absorbed: f64,
    pub soil_moisture_pct: f64,
    pub soil_n: f64,
    pub soil_p: f64,
    pub soil_k: f64,
    pub soil_ph: f64,
    pub soil_temp_c: f64,
    pub lai: f64,
    pub total_biomass_g: f64,
    pub leaf_g: f64,
    pub stem_g: f64,
    pub fruit_g: f64,
    pub fruit_count: u64,
    pub co2_ppm: f64,
    pub potential_et_mm: f64,
    pub wind_speed_ms: f64,
    pub cloud_cover_pct: f64,
}

impl DailyStats {
    pub fn sample(day: u64, atm: &Atmosphere, soil: &Soil,
                  plants: &[Plant], par: f64, lai: f64) -> Self {
        let mut leaf_g = 0.0;
        let mut stem_g = 0.0;
        let mut fruit_g = 0.0;
        let mut fruit_count = 0u64;
        for p in plants {
            leaf_g += p.leaf_g;
            stem_g += p.stem_g;
            fruit_g += p.fruit_g;
            fruit_count += p.fruit_count();
        }
        let total_biomass_g = leaf_g + stem_g + fruit_g + plants.iter().map(|p| p.root_g).sum::<f64>();
        Self {
            day,
            air_temp_c: atm.air_temp_c,
            rainfall_mm: atm.rainfall_mm,
            par_absorbed: par,
            soil_moisture_pct: soil.surface_water_pct() * 100.0,
            soil_n: soil.surface_n(),
            soil_p: soil.surface_p(),
            soil_k: soil.surface_k(),
            soil_ph: soil.ph(),
            soil_temp_c: soil.top().temp_c,
            lai,
            total_biomass_g,
            leaf_g, stem_g, fruit_g,
            fruit_count,
            co2_ppm: atm.co2_ppm(),
            potential_et_mm: atm.potential_et_mm,
            wind_speed_ms: atm.wind_speed_ms,
            cloud_cover_pct: atm.cloud_cover_pct,
        }
    }
}

/// 一维锥状统计 (流式 μ/min/max/σ)
#[derive(Clone, Debug, Default)]
pub struct Cone1D {
    count: u64,
    min: f64, max: f64, mean: f64, m2: f64,
    alpha: f64, ema1: f64, ema2: f64, initialized: bool,
}

impl Cone1D {
    pub fn new(alpha: f64) -> Self {
        let mut s = Self::default(); s.alpha = alpha.clamp(0.001, 1.0); s
    }
    pub fn push(&mut self, x: f64) {
        self.count += 1;
        if self.count == 1 { self.min = x; self.max = x; self.mean = x; self.m2 = 0.0;
                             self.ema1 = x; self.ema2 = x; self.initialized = true; return; }
        if x < self.min { self.min = x; }
        if x > self.max { self.max = x; }
        let delta = x - self.mean;
        self.mean += delta / self.count as f64;
        self.m2 += delta * (x - self.mean);
        // DEMA
        self.ema1 = self.alpha * x + (1.0 - self.alpha) * self.ema1;
        self.ema2 = self.alpha * self.ema1 + (1.0 - self.alpha) * self.ema2;
    }
    /// 去趋势 (DEMA)
    #[inline] pub fn dema(&self) -> f64 { 2.0 * self.ema1 - self.ema2 }
    #[inline] pub fn mean(&self)  -> f64 { self.mean }
    #[inline] pub fn min(&self)   -> f64 { self.min }
    #[inline] pub fn max(&self)   -> f64 { self.max }
    #[inline] pub fn stddev(&self) -> f64 {
        if self.count < 2 { 0.0 } else { (self.m2 / (self.count - 1) as f64).sqrt() }
    }
    /// 异常分数 = |x - dema| / σ  (Z)
    pub fn anomaly_score(&self, x: f64) -> f64 {
        let sd = self.stddev();
        if sd < 1e-9 { 0.0 } else { (x - self.dema()).abs() / sd }
    }
}

/// 锥状通道 (固定 5 个核心生态通道)
pub struct EcoCone {
    pub temp:  Cone1D,
    pub rain:  Cone1D,
    pub swc:   Cone1D,  // 土壤水分
    pub n_pool: Cone1D,
    pub biomass: Cone1D,
}

impl EcoCone {
    pub fn new(alpha: f64) -> Self {
        Self {
            temp: Cone1D::new(alpha),
            rain: Cone1D::new(alpha),
            swc:  Cone1D::new(alpha),
            n_pool: Cone1D::new(alpha),
            biomass: Cone1D::new(alpha),
        }
    }
    pub fn push(&mut self, s: &DailyStats) {
        self.temp.push(s.air_temp_c);
        self.rain.push(s.rainfall_mm);
        self.swc.push(s.soil_moisture_pct);
        self.n_pool.push(s.soil_n);
        self.biomass.push(s.total_biomass_g);
    }
    /// 把当前状态序列化
    pub fn snapshot(&self) -> [f64; 25] {
        let mut o = [0.0_f64; 25];
        let c = [&self.temp,&self.rain,&self.swc,&self.n_pool,&self.biomass];
        for (i,c) in c.iter().enumerate() {
            o[i*5+0] = c.min();
            o[i*5+1] = c.max();
            o[i*5+2] = c.mean();
            o[i*5+3] = c.stddev();
            o[i*5+4] = c.dema();
        }
        o
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cone1d_stddev() {
        let mut c = Cone1D::new(0.2);
        for x in 1..=100 { c.push(x as f64); }
        assert!((c.mean() - 50.5).abs() < 1e-9);
        assert!(c.stddev() > 0.0);
    }

    #[test]
    fn cone1d_anomaly_far() {
        let mut c = Cone1D::new(0.2);
        // 必须有 σ > 0 才能计算 Z-score
        for i in 0..100 { c.push(10.0 + (i as f64) * 0.01); }
        assert!(c.anomaly_score(20.0) > 5.0, "20 is far from mean with non-zero σ");
    }

    #[test]
    fn eco_cone_snapshot_len() {
        let cone = EcoCone::new(0.1);
        let s = cone.snapshot();
        assert_eq!(s.len(), 25);
    }
}
