"""Streamlit chrome localization helpers.

Streamlit does not expose a first-class language pack for its built-in browser
chrome, so the app applies a small client-side localization pass for the few
system menu labels that may still be visible in viewer mode.
"""

from __future__ import annotations

import json

import streamlit.components.v1 as components

STREAMLIT_CHROME_TRANSLATIONS: dict[str, str] = {
    "File change.": "文件已变更。",
    "Rerun": "重新运行",
    "Always rerun": "始终重新运行",
    "Auto rerun": "自动重新运行",
    "Clear cache": "清除缓存",
    "Print": "打印",
    "Record screen": "录制屏幕",
    "System": "跟随系统",
    "Light": "浅色",
    "Dark": "深色",
    "Use system setting": "跟随系统设置",
    "Made with Streamlit": "基于 Streamlit 构建",
    "Main menu": "主菜单",
    "Settings": "设置",
    "Deploy": "部署",
    "Deploy this app using...": "选择部署方式",
    "Streamlit Community Cloud": "Streamlit 社区云",
    "For community, always free": "面向社区，永久免费",
    "For personal hobbies and learning": "适合个人兴趣和学习",
    "Deploy unlimited public apps": "可部署不限数量的公开应用",
    "Explore and learn from Streamlit’s community and popular apps": (
        "探索并学习 Streamlit 社区和热门应用"
    ),
    "Deploy now": "立即部署",
    "Learn more": "了解更多",
    "Snowflake": "Snowflake",
    "For enterprise": "面向企业",
    "Enterprise-level security, support, and fully managed infrastructure": (
        "企业级安全、支持和全托管基础设施"
    ),
    "Deploy unlimited private apps with role-based sharing": (
        "可部署不限数量的私有应用，并支持基于角色共享"
    ),
    "Integrate with Snowflake’s full data stack": "集成 Snowflake 完整数据栈",
    "Start trial": "开始试用",
    "Other platforms": "其他平台",
    "For custom deployment": "适合自定义部署",
    "Deploy on your own hardware or cloud service": "部署到自有硬件或云服务",
    "Set up and maintain your own authentication, resources, and costs": (
        "自行配置和维护认证、资源和成本"
    ),
    "Close": "关闭",
    "Checkmark": "勾选",
    "Streamlit Logo": "Streamlit 标志",
    "Rocket": "火箭",
}


def build_streamlit_chrome_localizer_html() -> str:
    """Return the hidden component HTML that localizes Streamlit chrome text."""
    translations_json = json.dumps(
        STREAMLIT_CHROME_TRANSLATIONS,
        ensure_ascii=False,
    )
    return f"""
<script>
(function () {{
  const translations = {translations_json};
  const normalize = (value) => String(value || "").replace(/\\s+/g, " ").trim();

  function translate(value) {{
    const text = normalize(value);
    if (!text) {{
      return value;
    }}
    if (translations[text]) {{
      return translations[text];
    }}
    if (text.startsWith("Made with Streamlit")) {{
      return text.replace("Made with Streamlit", translations["Made with Streamlit"]);
    }}
    return value;
  }}

  function getTargetDocument() {{
    try {{
      if (window.parent && window.parent.document) {{
        return window.parent.document;
      }}
    }} catch (error) {{
      return document;
    }}
    return document;
  }}

  function translateTextNodes(root) {{
    if (!root) {{
      return;
    }}
    const walker = root.createTreeWalker(
      root.body || root,
      NodeFilter.SHOW_TEXT,
      {{
        acceptNode(node) {{
          const parent = node.parentElement;
          if (!parent || ["SCRIPT", "STYLE", "TEXTAREA"].includes(parent.tagName)) {{
            return NodeFilter.FILTER_REJECT;
          }}
          return normalize(node.nodeValue)
            ? NodeFilter.FILTER_ACCEPT
            : NodeFilter.FILTER_REJECT;
        }},
      }}
    );
    const nodes = [];
    while (walker.nextNode()) {{
      nodes.push(walker.currentNode);
    }}
    for (const node of nodes) {{
      const translated = translate(node.nodeValue);
      if (translated !== node.nodeValue) {{
        node.nodeValue = translated;
      }}
    }}
  }}

  function translateAttributes(root) {{
    if (!root || !root.body) {{
      return;
    }}
    const attributes = ["aria-label", "title", "alt"];
    for (const element of root.body.querySelectorAll("*")) {{
      for (const attribute of attributes) {{
        if (!element.hasAttribute(attribute)) {{
          continue;
        }}
        const value = element.getAttribute(attribute);
        const translated = translate(value);
        if (translated !== value) {{
          element.setAttribute(attribute, translated);
        }}
      }}
    }}
  }}

  function localize() {{
    const targetDocument = getTargetDocument();
    translateTextNodes(targetDocument);
    translateAttributes(targetDocument);
  }}

  const targetDocument = getTargetDocument();
  localize();
  if (targetDocument && targetDocument.body) {{
    const observer = new MutationObserver(localize);
    observer.observe(targetDocument.body, {{
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["aria-label", "title", "alt"],
    }});
  }}
}})();
</script>
"""


def apply_streamlit_chrome_localization() -> None:
    """Install the hidden component that localizes Streamlit's built-in chrome."""
    components.html(
        build_streamlit_chrome_localizer_html(),
        height=0,
        width=0,
    )
