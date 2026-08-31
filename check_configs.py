#!/usr/bin/env python3
"""
V2Ray Config Checker
Проверяет доступность репозиториев с v2ray конфигами
"""

import requests
import json
from datetime import datetime
import os

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
    """
    Проверяет доступность GitHub репозитория
    repo_path формата: owner/repo
    """
    try:
        url = f"https://api.github.com/repos/{repo_path}"
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка при проверке {repo_path}: {str(e)}")
        return False

def get_repo_info(repo_path):
    """
    Получает информацию о репозитории
    """
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

def main():
    print("\n" + "="*60)
    print(f"🚀 V2Ray Config Checker запущен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    # Загружаем список источников
    sources = load_sources()
    
    if not sources:
        print("❌ Нет источников для проверки!")
        return
    
    print(f"📋 Найдено источников для проверки: {len(sources)}\n")
    
    working_repos = []
    failed_repos = []
    
    # Проверяем каждый источник
    for i, repo in enumerate(sources, 1):
        print(f"[{i}/{len(sources)}] Проверяю: {repo}...", end=" ")
        
        if check_github_repo(repo):
            info = get_repo_info(repo)
            if info:
                working_repos.append({
                    'repo': repo,
                    'info': info
                })
                print(f"✅ OK (⭐ {info['stars']} stars)")
            else:
                failed_repos.append(repo)
                print("⚠️  Не удалось получить информацию")
        else:
            failed_repos.append(repo)
            print("❌ НЕДОСТУПЕН")
    
    # Сохраняем результаты в JSON
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_checked': len(sources),
        'working': len(working_repos),
        'failed': len(failed_repos),
        'working_repos': working_repos,
        'failed_repos': failed_repos
    }
    
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Сохраняем в текстовый формат
    with open('WORKING_CONFIGS.md', 'w', encoding='utf-8') as f:
        f.write(f"# ✅ Рабочие V2Ray конфиги\n\n")
        f.write(f"**Последняя проверка:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Статистика:**\n")
        f.write(f"- ✅ Рабочих: {len(working_repos)}\n")
        f.write(f"- ❌ Недоступных: {len(failed_repos)}\n")
        f.write(f"- 📊 Всего проверено: {len(sources)}\n\n")
        
        if working_repos:
            f.write(f"## Рабочие источники:\n\n")
            for item in working_repos:
                repo = item['repo']
                info = item['info']
                f.write(f"### [{repo}]({info['url']})\n")
                f.write(f"- ⭐ Stars: {info['stars']}\n")
                f.write(f"- 🕐 Обновлено: {info['updated']}\n")
                f.write(f"- 📌 Статус: {info['status']}\n\n")
        
        if failed_repos:
            f.write(f"## ❌ Недоступные источники:\n\n")
            for repo in failed_repos:
                f.write(f"- `{repo}`\n")
    
    # Выводим итоги
    print("\n" + "="*60)
    print(f"✅ Проверка завершена!")
    print(f"   Рабочих: {len(working_repos)}")
    print(f"   Недоступных: {len(failed_repos)}")
    print(f"   Результаты сохранены в WORKING_CONFIGS.md и results.json")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
