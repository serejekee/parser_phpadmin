import requests
from bs4 import BeautifulSoup
import sys
import csv
from datetime import datetime


def main():
    base_url = "http://185.244.219.162/phpmyadmin/"
    username = "test"
    password = "JHFBdsyf2eg8*"
    db_name = "testDB"
    table_name = "users"

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })

    try:
        print("Шаг 1: Получение страницы входа и токена...")
        response = session.get(base_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        token_input = soup.find('input', {'name': 'token'})
        if not token_input:
            print("Ошибка: не удалось найти токен на странице входа.")
            sys.exit(1)
        token = token_input['value']
        print(f"Токен получен: {token[:10]}...")

        print("\nШаг 2: Авторизация...")
        login_data = {
            'pma_username': username,
            'pma_password': password,
            'server': '1',
            'token': token
        }
        response = session.post(base_url + 'index.php', data=login_data)
        response.raise_for_status()

        if 'token' not in session.cookies and "access denied" in response.text.lower():
            print("Ошибка: не удалось авторизоваться. Проверьте логин и пароль.")
            sys.exit(1)
        print("Авторизация прошла успешно.")

        soup = BeautifulSoup(response.text, 'html.parser')
        token_input = soup.find('input', {'name': 'token'})
        if token_input:
            token = token_input['value']
        else:
            if 'token=' in response.url:
                token = response.url.split('token=')[1].split('&')[0]
            else:
                print("Ошибка: не удалось получить токен после авторизации.")
                sys.exit(1)
        print(f"Новый токен для сессии: {token[:10]}...")

        print(f"\nШаг 3a: Проверка доступных баз данных...")
        db_list_url = f"{base_url}index.php"
        db_params = {'token': token}
        db_response = session.get(db_list_url, params=db_params)
        db_response.raise_for_status()

        if db_name not in db_response.text:
            print(f"База данных '{db_name}' не найдена. Доступные базы данных:")
            soup_db = BeautifulSoup(db_response.text, 'html.parser')
            db_links = soup_db.find_all('a', href=lambda href: href and 'db=' in href)
            for link in db_links[:10]:
                if 'db=' in link.get('href', ''):
                    db_found = link.get('href').split('db=')[1].split('&')[0]
                    print(f"  - {db_found}")
            sys.exit(1)
        
        print(f"База данных '{db_name}' найдена.")

        print(f"\nШаг 3b: Проверка таблиц в базе '{db_name}'...")
        db_url = f"{base_url}index.php"
        db_params = {'db': db_name, 'token': token}
        db_tables_response = session.get(db_url, params=db_params)
        db_tables_response.raise_for_status()

        if table_name not in db_tables_response.text:
            print(f"Таблица '{table_name}' не найдена в базе '{db_name}'. Доступные таблицы:")
            soup_tables = BeautifulSoup(db_tables_response.text, 'html.parser')
            table_links = soup_tables.find_all('a', href=lambda href: href and 'table=' in href)
            for link in table_links[:10]:
                if 'table=' in link.get('href', ''):
                    table_found = link.get('href').split('table=')[1].split('&')[0]
                    print(f"  - {table_found}")
            sys.exit(1)
        
        print(f"Таблица '{table_name}' найдена.")

        print(f"\nШаг 3c: Просмотр содержимого таблицы '{table_name}'...")
        browse_url = f"{base_url}index.php"
        browse_params = {
            'db': db_name,
            'table': table_name,
            'token': token
        }
        
        response = session.get(browse_url, params=browse_params)
        response.raise_for_status()
        response.encoding = 'utf-8'

        print("\nШаг 4: Парсинг HTML и извлечение данных...")
        
        soup_table = BeautifulSoup(response.text, 'lxml')

        table = soup_table.select_one('table.table_results.data')
            
        if not table:
            print("Ошибка: не удалось найти таблицу с данными (table.table_results.data) на странице.")
            sys.exit(1)
            
        thead = table.find('thead')
        if not thead:
            print("Ошибка: не удалось найти заголовок (thead) в таблице.")
            sys.exit(1)

        headers = [header.text.strip() for header in thead.find_all('th')]
        print(f"Отладка - заголовки таблицы: {headers}")

        try:
            id_index = -1
            name_index = -1

            for i, h in enumerate(headers):
                if h.startswith('id'):
                    id_index = i
                elif h == 'name':
                    name_index = i
            
            if id_index == -1 or name_index == -1:
                raise ValueError("Не удалось найти столбцы 'id' и 'name'")

            print(f"Отладка - индекс id: {id_index}, индекс name: {name_index}")
        except ValueError as e:
            print(f"Ошибка: {e}")
            print(f"Найденные заголовки: {headers}")
            sys.exit(1)

        rows_data = []
        tbody = table.find('tbody')
        if not tbody:
            print("Ошибка: не удалось найти тело (tbody) в таблице.")
            sys.exit(1)

        for tr in tbody.find_all('tr'):
            cells = [cell.text.strip() for cell in tr.find_all(['td', 'th'])]

            if len(cells) > 5:
                user_id = cells[4]
                user_name = cells[5]

                if user_id.isdigit():
                    rows_data.append([user_id, user_name])

        if not rows_data:
            print("Данные для 'id' и 'name' не найдены в таблице.")
            return

        output_headers = ['id', 'name']
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"users_{timestamp}.csv"

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(output_headers)
            writer.writerows(rows_data)

        print(f"\nДанные (id, name) успешно сохранены в файл: {filename}")
        print(f"Количество строк (включая заголовок): {len(rows_data) + 1}")

        print("\nПредварительный просмотр данных:")
        print(" | ".join(output_headers))
        print("-" * (len(" | ".join(output_headers))))
        for row in rows_data[:5]:
            print(" | ".join(row))
        if len(rows_data) > 5:
            print(f"... и еще {len(rows_data) - 5} строк(и)")

    except requests.exceptions.RequestException as e:
        print(f"\nПроизошла ошибка HTTP: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nПроизошла непредвиденная ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
