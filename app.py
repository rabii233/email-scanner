from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan_emails', methods=['POST'])
def scan_emails():
    data = request.json
    urls = data.get('urls', [])
    
    if not urls:
        return jsonify({"error": "Aucune URL fournie."}), 400

    all_found_emails = []

    for url_str in urls:
        try:
            if not url_str.startswith('http://') and not url_str.startswith('https://'):
                url_str = 'http://' + url_str

            response = requests.get(url_str, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            page_content = soup.get_text()

            found_visible_emails = set(EMAIL_REGEX.findall(page_content))
            for email in found_visible_emails:
                all_found_emails.append({
                    "email": email,
                    "domain_source": url_str,
                    "type": "Direct",
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            masked_patterns = re.findall(r'(\w+)\s*\[?\(?at\)?\]?\s*(\w+)\s*\[?\(?dot\)?\]?\s*(\w+)', page_content, re.IGNORECASE)
            for parts in masked_patterns:
                reconstructed_email = f"{parts[0]}@{parts[1]}.{parts[2]}"
                if EMAIL_REGEX.match(reconstructed_email):
                    all_found_emails.append({
                        "email": reconstructed_email,
                        "domain_source": url_str,
                        "type": "Masqué/Reconstruit",
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

        except requests.exceptions.RequestException as e:
            all_found_emails.append({
                "email": f"Erreur: {e}",
                "domain_source": url_str,
                "type": "Erreur",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception as e:
            all_found_emails.append({
                "email": f"Erreur inattendue: {e}",
                "domain_source": url_str,
                "type": "Erreur",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    unique_emails_dict = {}
    for item in all_found_emails:
        email_key = item['email'].lower()
        if email_key not in unique_emails_dict:
            unique_emails_dict[email_key] = item
    
    unique_results = list(unique_emails_dict.values())

    return jsonify({"emails": unique_results})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
