#!/usr/bin/env python3
"""检测后台登录页面是否存在弱口令。"""

import argparse
import os
import re
from urllib.parse import urljoin

import requests

URLS_FILE = "urls.txt"
LOGIN_PATHS = ["/login", "/login.php"]
# 按顺序尝试；DVWA 默认口令是 admin/password，可按需增删
CREDENTIALS = [
    ("admin", "admin"),
    ("admin", "password"),
]
SUCCESS_MARKERS = ("Dashboard", "Welcome", "Logout")
FAILURE_MARKERS = ("login failed", "incorrect", "invalid credentials", "用户名或密码")
TIMEOUT = 10


def read_urls(filepath: str) -> list[str]:
    """从文件中读取网址列表，忽略空行和以 # 开头的注释行。"""
    urls = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if url and not url.startswith("#"):
                urls.append(url)
    return urls


def is_login_success(response: requests.Response, login_url: str) -> bool:
    """根据跳转后的最终页面判断是否真正登录成功。"""
    text = response.text
    text_lower = text.lower()
    final_url = response.url.lower()
    login_page = login_url.rstrip("/").split("/")[-1].lower()

    if any(marker in text_lower for marker in FAILURE_MARKERS):
        return False

    # 仍停留在登录页且没有成功标志 → 失败（避免 DVWA 错误口令也返回 302 的误报）
    if login_page in final_url and not any(marker in text for marker in SUCCESS_MARKERS):
        return False

    return any(marker in text for marker in SUCCESS_MARKERS)


def try_login(
    session: requests.Session,
    base_url: str,
    login_path: str,
    username: str,
    password: str,
    verbose: bool,
) -> tuple[bool, str]:
    login_url = urljoin(base_url.rstrip("/") + "/", login_path.lstrip("/"))

    get_resp = session.get(login_url, timeout=TIMEOUT)
    if verbose:
        print(f"  GET {login_url} -> {get_resp.status_code}")

    if get_resp.status_code >= 400:
        return False, f"登录页不可达 (HTTP {get_resp.status_code})"

    payload = {"username": username, "password": password}
    token_match = re.search(
        r"name=['\"]user_token['\"]\s+value=['\"]([^'\"]+)['\"]",
        get_resp.text,
    )
    if token_match:
        payload["user_token"] = token_match.group(1)
        payload["Login"] = "Login"

    post_resp = session.post(
        login_url,
        data=payload,
        timeout=TIMEOUT,
        allow_redirects=True,
    )
    if verbose:
        print(
            f"  POST {login_url} ({username}/{password}) -> "
            f"{post_resp.status_code}, 最终URL: {post_resp.url}"
        )

    if is_login_success(post_resp, login_url):
        return True, login_path

    return False, f"HTTP {post_resp.status_code}, 未登录成功"


def check_weak_password(base_url: str, verbose: bool = False) -> tuple[bool, str]:
    """尝试弱口令登录，返回 (是否成功, 详情)。"""
    session = requests.Session()
    last_detail = "所有登录路径和口令均失败"

    for login_path in LOGIN_PATHS:
        for username, password in CREDENTIALS:
            ok, detail = try_login(
                session, base_url, login_path, username, password, verbose
            )
            if ok:
                return True, f"{login_path} ({username}/{password})"
            last_detail = detail
            if verbose:
                print(f"  失败: {login_path} {username}/{password} — {detail}")

    return False, last_detail


def main() -> None:
    parser = argparse.ArgumentParser(description="弱口令检测")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="显示详细请求信息"
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    urls_path = os.path.join(script_dir, URLS_FILE)

    if not os.path.isfile(urls_path):
        print(f"错误: 未找到 {URLS_FILE}")
        return

    urls = read_urls(urls_path)
    if not urls:
        print(f"警告: {URLS_FILE} 中没有有效网址")
        return

    for url in urls:
        try:
            if args.verbose:
                print(f"\n检测: {url}")
            ok, detail = check_weak_password(url, verbose=args.verbose)
            if ok:
                print(f"可能存在弱口令: {url} [{detail}]")
            else:
                suffix = f" ({detail})" if args.verbose else ""
                print(f"失败: {url}{suffix}")
        except requests.exceptions.Timeout:
            print(f"失败: {url} (请求超时，检查网络或增大 TIMEOUT)")
        except requests.exceptions.ConnectionError:
            print(f"失败: {url} (连接失败，目标不可达)")
        except requests.exceptions.RequestException as e:
            print(f"失败: {url} ({e})")
        except Exception as e:
            print(f"失败: {url} (未知错误: {e})")


if __name__ == "__main__":
    main()
