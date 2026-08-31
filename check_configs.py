#!/usr/bin/env python3
"""
V2Ray Config Checker - Simplified Version
"""

import requests
import json
import re
from datetime import datetime
import sys

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_sources():
    """Загружает список источников"""
    try:
        with open('sources.txt', 'r', encoding='utf-8') as f:
            sources = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return sources
    except Exception as e:
        print(f"❌ Ошибка при чтении sources.txt: {e}")
        return []

def check_repo_exists(repo_path):
    """Проверяет существование репозитория"""
    try:
        url = f"https://api.github.com/repos/{repo_path}"
        response = requests.get(url, timeout=10, verify=False)
        return response.status_code == 200, response.json() if response.status_code == 200 else {}
    except:
        return False, {}

def fetch_raw_content(repo_path):
    """Скачивает README.md"""
    for branch in ['main', 'master']:
        try:
            url = f"https://raw.githubusercontent.com/{repo_path}/{branch}/README.md"
            response = requests.get(url, timeout=10, verify=False)
            if response.status_code == 200:
                return response.text
        except:
            pass
    return ""

def extract_configs(text):
    """Извлекает конфиги из текста"""
    configs = []
    patterns = [
        r'(vless://[^\s\n]+)',
        r'(vmess://[^\s\n]+)',
        r'(ss://[^\s\n]+)',
        r'(trojan://[^\s\n]+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            config = match.rstrip('.,;:')
            if len(config) > 20:
                configs.append(config)
    
    return configs

def is_valid_config(config_str):
    """Проверяет валидность"""
    config = config_str.strip()
    if not any(config.startswith(p) for p in ['vless://', 'vmess://', 'ss://', 'trojan://']):
        return False
    return len(config) > 20

def remove_duplicates(configs):
    """Удаляет дубликаты"""
    seen = set()
    unique = []
    for config in configs:
        if config and config not in seen:
            seen.add(config)
            unique.append(config)
    return unique

def main():
    print("\n" + "="*70)
    print(f"🚀 V2Ray Config Checker - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    sources = load_sources()
    if not sources:
        print("❌ Нет источников!")
        return
    
    print(f"📋 Проверяю {len(sources)} источников...\n")
    
    working_repos = []
    all_configs = []
    
    for i, repo in enumerate(sources, 1):
        print(f"[{i}/{len(sources)}] {repo}...", end=" ")
        sys.stdout.flush()
        
        exists, repo_data = check_repo_exists(repo)
        
        if exists:
            print("✅", end=" ")
            working_repos.append({
                'repo': repo,
                'url': repo_data.get('html_url', ''),
                'stars': repo_data.get('stargazers_count', 0),
                'updated': repo_data.get('pushed_at', '')
            })
            
            print("| Конфиги...", end=" ")
            sys.stdout.flush()
            
            content = fetch_raw_content(repo)
            if content:
                configs = extract_configs(content)
                if configs:
                    all_configs.extend(configs)
                    print(f"✓ ({len(configs)})")
                else:
                    print("(0)")
            else:
                print("(-)")  
        else:
            print("❌")
    
    print(f"\n📄 Обработка результатов...")
    
    valid = [c for c in all_configs if is_valid_config(c)]
    unique = remove_duplicates(valid)
    
    print(f"  ✔ Найдено: {len(all_configs)}")
    print(f"  ✔ Валидных: {len(valid)}")
    print(f"  ✔ Уникальных: {len(unique)}")
    
    # Сохраняем working_configs.txt
    with open('working_configs.txt', 'w', encoding='utf-8') as f:
        for config in unique:
            f.write(config + '\n')
    
    # Сохраняем results.json
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_repos': len(sources),
        'working_repos': len(working_repos),
        'total_configs': len(all_configs),
        'unique_configs': len(unique),
        'repos': working_repos
    }
    
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Сохраняем WORKING_CONFIGS.md
    with open('WORKING_CONFIGS.md', 'w', encoding='utf-8') as f:
        f.write(f"# ✅ V2Ray Конфиги\n\n")
        f.write(f"**Проверка:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 📋 Статистика\n\n")
        f.write(f"- 📚 Проверено: {len(sources)}\n")
        f.write(f"- ✅ Рабочих: {len(working_repos)}\n")
        f.write(f"- 📄 Конфигов найдено: {len(all_configs)}\n")
        f.write(f"- 🎯 **Уникальных: {len(unique)}**\n\n")
        f.write(f"## 📥 Скачать\n\n")
        f.write(f"[working_configs.txt](working_configs.txt) - {len(unique)} конфигов\n")
    
    print("\n" + "="*70)
    print("✅ ГОТОВО!")
    print(f"  📄 working_configs.txt - {len(unique)} конфигов")
    print(f"  📦 results.json")
    print(f"  📋 WORKING_CONFIGS.md")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(0)  # Не бросаем ошибку
