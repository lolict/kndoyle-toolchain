// ══════════════════════════════════════════════════════════════════
// plant.rs — 个体植株 (根 · 茎 · 叶 · 花 · 果 · 生物量分配)
// ══════════════════════════════════════════════════════════════════
//
// 植物生长简化模型 (基于 Monteith 光能利用率):
//   · ΔB = ε·PAR_abs·f_T·f_W·f_N·f_P·f_K   [g/m²/day]
//   · 分配系数: 营养期 → 多叶; 花期 → 花果; 黄熟期 → 种子
//   · 叶面积指数 LAI ∝ 叶生物量·SLA
//   · 气孔导度耦合水分胁迫
//   · 果实数量 ∝ 花期同化 - 败育率 (受 W/N 胁迫)
//   · 有机质还田 (枯枝落叶) → 下一代循环

use crate::eco::atmosphere::Atmosphere;
use crate::eco::soil::Soil;

#[derive(Clone, Debug)]
pub struct PlantConfig {
    pub name: &'static str,
    pub epsilon: f64,        // 光能利用率 g CO2 / MJ PAR
    pub sla: f64,            // 比叶面积 m² leaf / g leaf
    pub max_height_m: f64,
    pub reproductive_biomass_threshold_g: f64, // 进入花期的生物量阈值 (g, 干重)
    pub fruit_per_g_flower: f64,
    pub fruit_g: f64,        // 单果干重 g
    pub cn_ratio_leaf: f64,  // 枯叶 C/N
    pub cn_ratio_wood: f64,
    pub frost_kill_c: f64,   // 霜冻温度阈值
    pub drought_mortality_threshold: f64, // 连续低于该 water_stress 天死亡
}

#[derive(Clone, Debug)]
pub enum PlantKind {
    Woody { name: String },
    Herb { name: String },
    Grass { name: String },
}

impl PlantKind {
    pub fn config(&self) -> PlantConfig {
        match self {
            PlantKind::Woody { .. } => PlantConfig {
                name: "木本", epsilon: 1.8, sla: 0.012, max_height_m: 12.0,
                reproductive_biomass_threshold_g: 500.0,
                fruit_per_g_flower: 0.05, fruit_g: 2.0,
                cn_ratio_leaf: 25.0, cn_ratio_wood: 80.0,
                frost_kill_c: -6.0, drought_mortality_threshold: 0.05,
            },
            PlantKind::Herb { .. } => PlantConfig {
                name: "草本", epsilon: 1.2, sla: 0.020, max_height_m: 1.5,
                reproductive_biomass_threshold_g: 300.0,
                fruit_per_g_flower: 0.20, fruit_g: 0.5,
                cn_ratio_leaf: 18.0, cn_ratio_wood: 40.0,
                frost_kill_c: -2.0, drought_mortality_threshold: 0.05,
            },
            PlantKind::Grass { .. } => PlantConfig {
                name: "禾草", epsilon: 1.6, sla: 0.025, max_height_m: 0.8,
                reproductive_biomass_threshold_g: 150.0,
                fruit_per_g_flower: 0.40, fruit_g: 0.1,
                cn_ratio_leaf: 15.0, cn_ratio_wood: 30.0,
                frost_kill_c: -3.0, drought_mortality_threshold: 0.03,
            },
        }
    }
    #[inline]
    pub fn name(&self) -> &str {
        match self { PlantKind::Woody { name } | PlantKind::Herb { name } | PlantKind::Grass { name } => name }
    }
}

#[derive(Clone, Debug)]
pub enum Stage {
    Seedling,
    Vegetative,
    Flowering,
    Fruiting,
    Senescent,   // 黄熟/衰老
    Dead,
}

#[derive(Clone, Debug)]
pub struct Plant {
    pub kind: PlantKind,
    pub cfg: PlantConfig,
    pub stage: Stage,
    pub age_days: u64,
    /// 各器官生物量 g
    pub root_g: f64,
    pub stem_g: f64,
    pub leaf_g: f64,
    pub flower_g: f64,
    pub fruit_g: f64,
    pub root_depth_m: f64,
    /// 胁迫状态
    pub water_stress_pct: f64,  // 0..1, 0=完全饱和
    pub n_stress_pct: f64,      // 0..1
    /// 枯死天数累计
    pub dead_stress_days: u64,
}

impl Plant {
    pub fn new(kind: PlantKind, age_days: u64) -> Self {
        let cfg = kind.config();
        Self {
            kind, cfg,
            stage: Stage::Seedling,
            age_days,
            root_g:    5.0,
            stem_g:   10.0,
            leaf_g:    5.0,
            flower_g:  0.0,
            fruit_g:   0.0,
            root_depth_m: 0.08,
            water_stress_pct: 1.0,
            n_stress_pct:     1.0,
            dead_stress_days: 0,
        }
    }

    pub fn biomass_g(&self) -> f64 {
        self.root_g + self.stem_g + self.leaf_g + self.flower_g + self.fruit_g
    }

    pub fn leaf_area_index(&self) -> f64 {
        (self.leaf_g * self.cfg.sla * 0.001).max(0.0)  // g*m²/g * 0.001 factor
    }

    pub fn height_m(&self) -> f64 {
        let h = (self.stem_g / 50.0).sqrt() * self.cfg.max_height_m / 2.0;
        h.min(self.cfg.max_height_m)
    }

    pub fn fruit_count(&self) -> u64 {
        (self.fruit_g / self.cfg.fruit_g).max(0.0) as u64
    }

    /// 蒸腾吸水 (mm) ∝ PAR · LAI · 水分应力抑制
    pub fn water_uptake_mm(&self) -> f64 {
        let lai = self.leaf_area_index();
        let uptake_coeff = 0.08; // mm·m²/MJ PAR
        let uptake = lai * self.water_stress_pct * uptake_coeff;
        uptake.max(0.0)
    }

    pub fn k_uptake_units(&self) -> f64 {
        self.biomass_g() * 0.00005
    }

    /// 每日生长推进
    pub fn tick(&mut self, atm: &Atmosphere, soil: &Soil, par_above_mj: f64) {
        // 是否已死
        if let Stage::Dead = self.stage { return; }

        let par = par_above_mj.max(0.0);

        // 1. 环境应力
        let ws = soil.top().water_stress();     // 0..1 (1=无水分胁迫)
        self.water_stress_pct = ws;
        // N 胁迫: 有效 N(g/m²) vs 需求
        let top_n_g_m2 = soil.surface_n() * 0.01;     // kg/ha → g/m² 粗估算
        let n_demand   = self.cfg.reproductive_biomass_threshold_g * 0.001;
        self.n_stress_pct = (top_n_g_m2 / n_demand.min(1.0)).clamp(0.0, 1.0);

        let tf_temp = self.temp_factor(atm.air_temp_c);

        // 2. 霜冻致死或严重胁迫
        if atm.air_temp_c < self.cfg.frost_kill_c {
            self.stage = Stage::Dead;
            return;
        }

        // 3. 生物量增量 (Monteith)
        let d_b = (self.cfg.epsilon * par * tf_temp
                 * self.water_stress_pct
                 * self.n_stress_pct
                 * (if atm.co2_ppm() > 0.0 { 1.0 } else { 1.0 }))
            .max(-5.0)   // 限制净损耗
            .min(30.0);  // 限幅
        let d_b = d_b.max(-self.biomass_g() * 0.05); // 一日净损耗上限

        if d_b < -0.01 {
            // 净消耗: 先烧叶 → 茎 → 根
            let burn = (-d_b).min(self.leaf_g);
            self.leaf_g -= burn;
            d_b + burn
        } else {
            d_b
        };

        // 4. 分配
        self.allocate(d_b);

        // 5. 阶段转变
        self.update_stage();

        // 6. 衰老积累
        if ws < self.cfg.drought_mortality_threshold {
            self.dead_stress_days += 1;
            if self.dead_stress_days > 14 {
                self.stage = Stage::Dead;
                // 凋落物进入土壤 (外部 carbon flux, 简化)
            }
        } else {
            self.dead_stress_days = self.dead_stress_days.saturating_sub(2);
        }

        // 7. 根系延伸
        if let Stage::Dead = self.stage {} else {
            self.root_depth_m = (self.root_depth_m + 0.001).min(1.5);
        }

        self.age_days += 1;
    }

    fn allocate(&mut self, d_b: f64) {
        if d_b <= 0.0 { return; }
        match &self.stage {
            Stage::Seedling | Stage::Vegetative => {
                self.leaf_g  += d_b * 0.50;
                self.stem_g  += d_b * 0.30;
                self.root_g  += d_b * 0.20;
            }
            Stage::Flowering => {
                self.leaf_g    += d_b * 0.25;
                self.stem_g    += d_b * 0.20;
                self.root_g    += d_b * 0.15;
                self.flower_g  += d_b * 0.40;
            }
            Stage::Fruiting => {
                self.leaf_g    += d_b * 0.15;
                self.stem_g    += d_b * 0.10;
                self.root_g    += d_b * 0.10;
                self.fruit_g   += d_b * 0.60;
                // 花逐步落尽
                self.flower_g = (self.flower_g - d_b * 0.3).max(0.0);
            }
            Stage::Senescent => {
                self.root_g += d_b * 0.4;
                // 叶逐步枯黄入土
                self.leaf_g = (self.leaf_g - d_b * 0.3).max(0.0);
                self.fruit_g += d_b * 0.6;  // 种子成熟
            }
            Stage::Dead => {}
        }
    }

    fn update_stage(&mut self) {
        let b = self.biomass_g();
        match &self.stage {
            Stage::Seedling if b > 30.0 => self.stage = Stage::Vegetative,
            Stage::Vegetative if b > self.cfg.reproductive_biomass_threshold_g => {
                self.stage = Stage::Flowering
            }
            Stage::Flowering if self.flower_g > 0.5 => self.stage = Stage::Fruiting,
            Stage::Fruiting if self.fruit_g > self.flower_g * self.cfg.fruit_per_g_flower * 10.0 => {
                self.stage = Stage::Senescent
            }
            Stage::Senescent if self.age_days > 365 => {
                self.stage = Stage::Dead
            }
            _ => {}
        }
    }

    fn temp_factor(&self, t: f64) -> f64 {
        // 钟形, 最适 25°C
        (-((t - 25.0).powi(2)) / 200.0).exp().clamp(0.0, 1.2)
    }

    pub fn hash_material(&self) -> Vec<u8> {
        let mut v = Vec::new();
        v.extend_from_slice(&self.biomass_g().to_be_bytes());
        v.extend_from_slice(&self.leaf_area_index().to_be_bytes());
        v.extend_from_slice(&self.age_days.to_be_bytes());
        v
    }
}

// ── Atmosphere 暴露 co2 (小 helper) ───────────────────────────────
impl Atmosphere {
    #[inline(always)]
    pub fn co2_ppm(&self) -> f64 { self.co2_ppm }
}
