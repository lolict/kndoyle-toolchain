// ╔══════════════════════════════════════════════════════════════════╗
// ║  满全法 · 囡囝共生元 — Rust 核心库                               ║
// ║  ManQuanFa · NanJian Symbiosis — Core Library                   ║
// ║                                                                  ║
// ║  Copyright © 刘楚恬 & lolict (七妹凹月留)                         ║
// ║  所有权保留 · 无 MIT / GPL / Apache 许可                          ║
// ╚══════════════════════════════════════════════════════════════════╝

// ── 满全法基础通信层 (v0.4) ──
pub mod mccp;
pub mod fsm;
pub mod kernel;
pub mod crypto;
pub mod protocol;

// ── 满全法综合扩展层 (v0.4 保留) ──
pub mod name_creator;
pub mod holo_3d;
pub mod log_ring;
pub mod time_node;
pub mod stats;
pub mod router;

// ── 满全法底层舞台 (v0.5 · 自举骨架) ──
// 五个子树自己可以独立 bootstrap:
//   triune   — 三元裁判机 (有无推演 / 流动方向 / 等效对齐)
//   funnel   — 漏斗控制器 (时间火候 + 空间切片 + 层级调度)
//   fractal  — 22亿节点分形调度器 (非残差/残差 + 收缩坍缩)
//   relational — 关系代数外壳 (身份→权重→流动权→优先级)
//   pleasure  — 愉悦值动力引擎 (吸引子 / 外界融合 / 唯一中心)
pub mod triune;
pub mod funnel;
pub mod fractal;
pub mod relational;
pub mod couple;
pub mod pleasure;

// ── 活生态系统 v0.5 (弃用方向: 以后只保留 eco 作为 metaphor 验证) ──
pub mod eco;

// ── 对外 re-export ──

// v0.4 基础层
pub use mccp::{Mccp, Kind, MCP_HUANHUN, MCP_ZHAOHUN, MCP_DALING, MCP_JIESHU, hanzi};
pub use fsm::FsmState;
pub use kernel::{CoupleOS, Process, ProcessState};
pub use crypto::Session;
pub use protocol::{Protocol, ProtocolState, Role, simulate_handshake_and_message};
pub use name_creator::{DragonL7, INITIALS, FINALS, RADICALS, char_to_dragon,
                       name_to_anchor_bytes, name_to_anchor, joint_anchor};
pub use holo_3d::{Coord3, syllable_to_index, index_to_syllable, hanzi_to_coord,
                  encode_mixedbase, decode_mixedbase, holographic_hash};
pub use log_ring::{LogEntry, LogRing, MerkleTree, HASH_LEN};
pub use time_node::{TimeNode, TimeCoord, SpaceCoord, unix_ms_to_timecoord, offset_to_space};
pub use stats::{StreamStats, Histogram, TimeWindowStats, SpaceDensity};
pub use router::{HEAVENLY_STEMS, EARTHLY_BRANCHES, ZODIAC, Pillar, BaZi,
                 gregorian_to_bazi, bazi_plus_name, bazi_16, bazi_to_coords,
                 bazi_to_hex_str, is_valid_pillar};
pub use eco::{Ecosystem, snapshot_hash};

// v0.5 底层舞台
pub use triune::{BeingState, FlowDirection, Funnel, Funnel as TriuneFunnel,
                 CollapseResult, TriuneVerdict, TriuneEngine};
pub use funnel::{TimeGovernor, SpaceBatcher, FunnelScheduler, CascadedFunnel,
                TimeLevel, SchedulerStatus};
pub use fractal::{FractalNode, FractalLevel, FractalGrid, FractalCollapseResult,
                  PhoneChipLayout, BILLION_NODE_TARGET, SpaceGridCoord, FractalOutput,
                  associative_scan, combine_fractal_nodes, ScanTree};
pub use relational::{Identity, Weight, FlowRight, Priority, Actor, Cluster,
                     Relation, RelationType, RelAlgebra};
pub use pleasure::{Pleasure, ExternalEntity, Attractor, SimplificationReport,
                   PleasureChain, ChainSummary};
pub use couple::{XiYaoProtocol, ManQuanFa, EclipseError, ManQuanFaStatus,
                 CoupleSoul, SoulState};
