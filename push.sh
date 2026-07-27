#!/usr/bin/env bash
# 混元项目四平台推送脚本（有备无患版）
# 用法：先在环境变量里放好各平台的仓库地址与令牌，再执行 bash push.sh
# 令牌只读环境变量，不落盘、不写进任何文件。
#
# 需要准备的环境变量（用到哪个平台就配哪个，不配的平台自动跳过）：
#   GITHUB_URL   例如 https://github.com/你的用户名/hunyuan.git
#   GITHUB_TOKEN GitHub 个人访问令牌（Settings → Developer settings → Tokens，scope 只勾 repo）
#   GITEE_URL    例如 https://gitee.com/你的用户名/hunyuan.git
#   GITEE_TOKEN  Gitee 私人令牌（设置 → 安全设置 → 私人令牌，只勾 projects 写权限）
#   GITCODE_URL  例如 https://gitcode.com/你的用户名/hunyuan.git
#   GITCODE_TOKEN
#   ATOMGIT_URL  例如 https://atomgit.com/你的用户名/hunyuan.git
#   ATOMGIT_TOKEN

set -u
cd "$(dirname "$0")"

push_to () {
    local name="$1" url_var="$2" token_var="$3"
    local url="${!url_var:-}" token="${!token_var:-}"
    if [ -z "$url" ] || [ -z "$token" ]; then
        echo "[跳过] $name：未配置 ${url_var} 或 ${token_var}"
        return 0
    fi
    # 把令牌临时拼进远程地址，推送完立刻移除，不留痕
    local authed
    authed=$(echo "$url" | sed "s#https://#https://oauth2:${token}@#")
    git remote remove "bak-$name" 2>/dev/null
    git remote add "bak-$name" "$authed"
    echo "[推送] $name ..."
    if git push "bak-$name" main; then
        echo "[成功] $name"
    else
        echo "[失败] $name（检查令牌权限与网络）"
    fi
    git remote remove "bak-$name"
}

git branch -M main 2>/dev/null
push_to github  GITHUB_URL  GITHUB_TOKEN
push_to gitee   GITEE_URL   GITEE_TOKEN
push_to gitcode GITCODE_URL GITCODE_TOKEN
push_to atomgit ATOMGIT_URL ATOMGIT_TOKEN
echo "全部处理完毕。"
