// gttx-runtime.js - 浏览器运行时 · 让浏览器解析我们的标签
// 原理: Web Components (customElements) + 自定义 script 类型
// 浏览器原生支持, 不需要任何服务器参与解析
//
// 标签注册:
//   <gkhtml>     显示链 · 前端渲染 (对应 ghktml 家族)
//   <gkndr>      关系链 · 关系运算
//   <mlil>       智能索引链 · 42进制编码/解码
//   <hftqml>     hf 融合系 · 语法容器

(function () {
    "use strict";

    // ============ 智能索引链 · 42 进制 (mlil) ============
    const COLOR_ROWS = [
        "红橙黄绿青蓝紫", "褐棕黑靛粉彩白", "朱绛赭丹彤缃黛",
        "翠碧缥素银金灰", "玉琅晶璃珀瑙璧", "曦辉霓旖靡暝黟",
    ];
    const NUM_FLAT = COLOR_ROWS.join("");

    function encode42(value, digits) {
        let v = value;
        let out = [];
        for (let i = 0; i < digits; i++) {
            out.unshift(NUM_FLAT[v % 42]);
            v = Math.floor(v / 42);
        }
        return out.join("");
    }
    function decode42(s) {
        let v = 0;
        for (const c of s) {
            const idx = NUM_FLAT.indexOf(c);
            if (idx < 0) return null;
            v = v * 42 + idx;
        }
        return v;
    }

    // ============ 显示链 · gkhtml 标签 ============
    class GkHtml extends HTMLElement {
        connectedCallback() {
            this.setAttribute("data-chain", "显示链");
            this.setAttribute("data-up", "gttx → 用户");
            this.style.display = "block";
            this.style.padding = "8px 12px";
            this.style.margin = "4px 0";
            this.style.borderLeft = "3px solid #7b5ea7";
            this.style.background = "#f7f5fb";
            this.style.borderRadius = "4px";
        }
    }

    // ============ 关系链 · gkndr 标签 ============
    class Gkndr extends HTMLElement {
        connectedCallback() {
            this.setAttribute("data-chain", "关系链");
            this.setAttribute("data-up", "gttx → 用户");
            this.style.display = "block";
            this.style.padding = "8px 12px";
            this.style.margin = "4px 0";
            this.style.borderLeft = "3px solid #3a7d5a";
            this.style.background = "#f0f7f3";
            this.style.borderRadius = "4px";
        }
    }

    // ============ 智能索引链 · mlil 标签 ============
    class Mlil extends HTMLElement {
        connectedCallback() {
            this.setAttribute("data-chain", "智能索引链");
            this.setAttribute("data-up", "gttx → 用户");
            this.style.display = "inline-block";
            this.style.padding = "2px 8px";
            this.style.margin = "2px";
            this.style.background = "#e8f0fe";
            this.style.border = "1px solid #aac3f0";
            this.style.borderRadius = "3px";
            this.style.fontFamily = "monospace";
            this.render();
        }
        static get observedAttributes() { return ["value"]; }
        attributeChangedCallback() {
            this.render();
        }
        render() {
            const v = parseInt(this.getAttribute("value") || "", 10);
            if (isNaN(v)) {
                this.textContent = "mlil: 缺 value 属性";
                return;
            }
            this.textContent = encode42(v, 3);
        }
    }

    // ============ hf 融合系 · hftqml 语法容器 ============
    class Hftqml extends HTMLElement {
        connectedCallback() {
            this.setAttribute("data-chain", "契约链");
            this.setAttribute("data-up", "gttx → 用户");
            this.style.display = "block";
            this.style.padding = "8px 12px";
            this.style.margin = "4px 0";
            this.style.border = "1px dashed #c77a3a";
            this.style.background = "#fdf6ee";
            this.style.borderRadius = "4px";
        }
    }

    // ============ 注册到浏览器 ============
    if (!customElements.get("gk-html")) customElements.define("gk-html", GkHtml);
    if (!customElements.get("gkndr")) customElements.define("gkndr", Gkndr);
    if (!customElements.get("mlil")) customElements.define("mlil", Mlil);
    if (!customElements.get("hftqml")) customElements.define("hftqml", Hftqml);

    // ============ 自定义脚本类型: <script type="text/gkhtml"> ============
    // 浏览器不认识这种 script 类型, 不会执行, 但会保留其文本内容.
    // 运行时读取它, 翻译成标准 DOM 渲染.
    function runGkScripts() {
        const scripts = document.querySelectorAll('script[type="text/gkhtml"]');
        scripts.forEach((script) => {
            const text = script.textContent.trim();
            const pre = document.createElement("pre");
            pre.textContent = "gkhtml 源码:\n" + text;
            pre.style.background = "#2d2d2d";
            pre.style.color = "#e0e0e0";
            pre.style.padding = "10px";
            pre.style.borderRadius = "4px";
            script.replaceWith(pre);
        });
    }

    // ============ 解析我们的 URI 协议头 ============
    // gkhtml://xx → 用自定义标签渲染; gttx://xx → 链式标记
    function parseGkUri() {
        document.querySelectorAll("[data-gk-uri]").forEach((el) => {
            const uri = el.getAttribute("data-gk-uri");
            const m = uri.match(/^(\w+):\/\/(.+)$/);
            if (m) {
                el.textContent = `协议[${m[1]}] → 资源[${m[2]}] · 附着 gttx 链`;
            }
        });
    }

    window.Gttx = {
        encode42,
        decode42,
        runGkScripts,
        parseGkUri,
        version: "0.1",
    };

    document.addEventListener("DOMContentLoaded", () => {
        runGkScripts();
        parseGkUri();
    });
})();
