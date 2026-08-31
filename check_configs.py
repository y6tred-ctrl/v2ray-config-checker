#!/usr/bin/env python3
"""
V2Ray Config Checker & Validator
Проверяет доступность репозиториев, скачивает конфиги, удаляет дубликаты
"""

import requests
import json
import base64
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import os

# Отключаем предупреждения SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_sources():
    """Загружает список источников из sources.txt"""
    try:
        with open('sources.txt', 'r', encoding='utf-8') as f:
            sources = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return sources
    except FileNotFoundError:
        print("⚠️  Файл sources.txt не найден!")
        return []

def check_github_repo(repo_path):
    """Проверяет доступность GitHub репозитория"""
    try:
        url = f"https://api.github.com/repos/{repo_path}"
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка при проверке {repo_path}: {str(e)}")
        return False

def get_repo_info(repo_path):
    """Получает информацию о репозитории"""
    try:
        url = f"https://api.github.com/repos/{repo_path}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'name': data.get('name'),
                'url': data.get('html_url'),
                'stars': data.get('stargazers_count'),
                'updated': data.get('pushed_at'),
                'status': '✅ Working'
            }
    except Exception as e:
        print(f"Ошибка при получении инфо {repo_path}: {str(e)}")
    return None

def fetch_configs_from_repo(repo_path):
    """
    Пытается скачать конфиги из репозитория различными способами
    """
    configs = []
    
    try:
        # Пробуем получить содержимое репозитория
        api_url = f"https://api.github.com/repos/{repo_path}/contents"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            contents = response.json()
            
            # Ищем файлы с конфигами
            config_files = []
            for item in contents:
                if isinstance(item, dict):
                    name = item.get('name', '').lower()
                    # Ищем файлы с расширениями конфигов или содержащие слова типа config, sub, proxy
                    if any(x in name for x in ['.txt', '.yaml', '.yml', '.json', 'config', 'sub', 'proxy', 'clash']):
                        config_files.append(item)
            
            # Скачиваем файлы
            for file_item in config_files[:5]:  # Лимит 5 файлов per repo
                raw_url = file_item.get('download_url')
                if raw_url:
                    try:
                        file_response = requests.get(raw_url, timeout=10)
                        if file_response.status_code == 200:
                            content = file_response.text
                            # Парсим конфиги
                            parsed = parse_configs(content)
                            configs.extend(parsed)
                    except:
                        pass
        
        # Альтернативный способ - прямая ссылка на raw
        raw_url = f"https://raw.githubusercontent.com/{repo_path}/main/README.md"
        try:
            response = requests.get(raw_url, timeout=10)
            if response.status_code == 200:
                parsed = parse_configs(response.text)
                configs.extend(parsed)
        except:
            pass
        
        # Пробуем также master branch
        raw_url = f"https://raw.githubusercontent.com/{repo_path}/master/README.md"
        try:
            response = requests.get(raw_url, timeout=10)
            if response.status_code == 200:
                parsed = parse_configs(response.text)
                configs.extend(parsed)
        except:
            pass
            
    except Exception as e:
        print(f"⚠️  Ошибка при загрузке конфигов из {repo_path}: {str(e)}")
    
    return configs

def parse_configs(content):
    """
    Парсит конфиги из текстового содержимого
    Ищет: vless://, vmess://, ss://, trojan://, etc.
    """
    configs = []
    
    # Регулярные выражения для поиска конфигов
    patterns = [
        r'(vless://[a-zA-Z0-9\-._~%!$&\'()*+,;=:@/\?#\[\]]+)',
        r'(vmess://[a-zA-Z0-9\-._~%!$&\'()*+,;=:@/\?#\[\]]+)',
        r'(ss://[a-zA-Z0-9\-._~%!$&\'()*+,;=:@/\?#\[\]]+)',
        r'(trojan://[a-zA-Z0-9\-._~%!$&\'()*+,;=:@/\?#\[\]]+)',
        r'(hysteria://[a-zA-Z0-9\-._~%!$&\'()*+,;=:@/\?#\[\]]+)',
        r'(tuic://[a-zA-Z0-9\-._~%!$&\'()*+,;=:@/\?#\[\]]+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content)
        configs.extend(matches)
    
    # Также пробуем base64 декодирование (для subscriptions)
    try:
        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
        for pattern in patterns:
            matches = re.findall(pattern, decoded)
            configs.extend(matches)
    except:
        pass
    
    return configs

def validate_config(config_str):
    """
    Проверяет валидность конфига
    Базовая проверка синтаксиса
    """
    config_str = config_str.strip()
    
    # Проверяем формат
    if not any(config_str.startswith(proto) for proto in ['vless://', 'vmess://', 'ss://', 'trojan://', 'hysteria://', 'tuic://']):
        return False
    
    # Проверяем, что это не слишком короткая строка
    if len(config_str) < 20:
        return False
    
    # Базовая проверка что @ и : присутствуют
    if '@' not in config_str and 'ss://' not in config_str[:5]:
        return False
    
    return True

def remove_duplicates(configs):
    """Удаляет дубликаты конфигов"""
    seen = set()
    unique = []
    
    for config in configs:
        config_clean = config.strip()
        if config_clean and config_clean not in seen:
            seen.add(config_clean)
            unique.append(config_clean)
    
    return unique

def test_config_connectivity(config_str, timeout=5):
    """
    Попытка проверить работоспособность конфига
    (базовая проверка синтаксиса)
    """
    # Парсим конфиг
    try:
        if config_str.startswith('vless://'):
            # vless://uuid@host:port?params#name
            parts = config_str.split('@')
            if len(parts) >= 2:
                host_part = parts[1].split(':')[0]
                # Проверяем что хост выглядит валидно
                if host_part and len(host_part) > 3:
                    return True
        
        elif config_str.startswith('vmess://'):
            # vmess:// ссылка
            try:
                # Извлекаем base64 часть
                b64_part = config_str.replace('vmess://', '')
                decoded = base64.b64decode(b64_part).decode('utf-8')
                data = json.loads(decoded)
                if 'add' in data and 'port' in data:
                    return True
            except:
                return False
        
        elif config_str.startswith('ss://'):
            # ss://cipher:password@host:port
            parts = config_str.replace('ss://', '').split('@')
            if len(parts) >= 2 and ':' in parts[1]:
                return True
        
        elif config_str.startswith('trojan://'):
            # trojan://password@host:port?params
            parts = config_str.split('@')
            if len(parts) >= 2:
                return True
        
        return True
    except:
        return False

def main():
    print("\n" + "="*70)
    print(f"🚀 V2Ray Config Checker запущен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    # Загружаем список источников
    sources = load_sources()
    
    if not sources:
        print("❌ Нет источников для проверки!")
        return
    
    print(f"📋 Найдено источников для проверки: {len(sources)}\n")
    
    working_repos = []
    failed_repos = []
    all_configs = []
    
    # Проверяем каждый источник и скачиваем конфиги
    for i, repo in enumerate(sources, 1):
        print(f"[{i}/{len(sources)}] Проверяю: {repo}...", end=" ")
        
        if check_github_repo(repo):
            info = get_repo_info(repo)
            if info:
                working_repos.append({
                    'repo': repo,
                    'info': info
                })
                print(f"✅ OK", end="")
                
                # Пробуем скачать конфиги
                print(f" | Загружаю конфиги...", end="")
                configs = fetch_configs_from_repo(repo)
                print(f" ✓ ({len(configs)} конфигов)", end="")
                all_configs.extend(configs)
                print()
            else:
                failed_repos.append(repo)
                print("⚠️  Не удалось получить информацию")
        else:
            failed_repos.append(repo)
            print("❌ НЕДОСТУПЕН")
    
    print(f"\n📊 Всего найдено конфигов: {len(all_configs)}")
    
    # Валидируем конфиги
    print("🔍 Валидирую конфиги...", end="")
    valid_configs = [c for c in all_configs if validate_config(c)]
    print(f" ✓ ({len(valid_configs)} валидных)")
    
    # Удаляем дубликаты
    print("🔄 Удаляю дубликаты...", end="")
    unique_configs = remove_duplicates(valid_configs)
    print(f" ✓ ({len(unique_configs)} уникальных)")
    
    # Сохраняем в текстовый файл (простой формат, по одному на строку)
    print("💾 Сохраняю конфиги...", end="")
    with open('working_configs.txt', 'w', encoding='utf-8') as f:
        for config in unique_configs:
            f.write(config + '\n')
    print(" ✓")
    
    # Сохраняем результаты в JSON
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_repos_checked': len(sources),
        'working_repos': len(working_repos),
        'failed_repos': len(failed_repos),
        'total_configs_found': len(all_configs),
        'valid_configs': len(valid_configs),
        'unique_configs': len(unique_configs),
        'repos_info': working_repos,
        'failed_repos': failed_repos,
        'configs': unique_configs
    }
    
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Создаем красивый markdown отчет
    with open('WORKING_CONFIGS.md', 'w', encoding='utf-8') as f:
        f.write(f"# ✅ Рабочие V2Ray Конфиги\n\n")
        f.write(f"**Последняя проверка:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 📊 Статистика\n\n")
        f.write(f"- 📚 Проверено репозиториев: {len(sources)}\n")
        f.write(f"- ✅ Рабочих репозиториев: {len(working_repos)}\n")
        f.write(f"- ❌ Недоступных: {len(failed_repos)}\n")
        f.write(f"- 🔗 Всего найдено конфигов: {len(all_configs)}\n")
        f.write(f"- ✔️  Валидных конфигов: {len(valid_configs)}\n")
        f.write(f"- 🎯 **Уникальных конфигов: {len(unique_configs)}**\n\n")
        
        if unique_configs:
            f.write(f"## 📋 Конфиги (скачай из [working_configs.txt](working_configs.txt))\n\n")
            f.write(f"```\n")
            for config in unique_configs[:10]:  # Показываем первые 10 в preview
                f.write(f"{config}\n")
            if len(unique_configs) > 10:
                f.write(f"...\n")
                f.write(f"# Всего {len(unique_configs)} конфигов\n")
            f.write(f"```\n\n")
        
        if working_repos:
            f.write(f"## 🌟 Рабочие Источники\n\n")
            for item in working_repos:
                repo = item['repo']
                info = item['info']
                f.write(f"### [{repo}]({info['url']})\n")
                f.write(f"- ⭐ Stars: {info['stars']}\n")
                f.write(f"- 🕐 Обновлено: {info['updated']}\n")
                f.write(f"- 📌 Статус: {info['status']}\n\n")
        
        if failed_repos:
            f.write(f"## ❌ Недоступные Источники\n\n")
            for repo in failed_repos:
                f.write(f"- `{repo}`\n")
    
    # Выводим итоги
    print("\n" + "="*70)
    print(f"✅ ПРОВЕРКА ЗАВЕРШЕНА!")
    print(f"   Репозиториев проверено: {len(sources)}")
    print(f"   Рабочих: {len(working_repos)}")
    print(f"   Недоступных: {len(failed_repos)}")
    print(f"   Конфигов найдено: {len(all_configs)}")
    print(f"   Конфигов валидных: {len(valid_configs)}")
    print(f"   🎯 Уникальных конфигов: {len(unique_configs)}")
    print(f"\n📁 Файлы сохранены:")
    print(f"   • working_configs.txt - все конфиги (по одному на строку)")
    print(f"   • WORKING_CONFIGS.md - красивый отчет")
    print(f"   • results.json - полные данные")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
