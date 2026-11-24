from flask import Flask, jsonify
import requests

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

@app.route("/api/meteo", methods=["GET"])
def get_meteo():
    # Coordenadas: Porto Alegre (Lat: -30.0332, Lon: -51.2300)
    # Período: 01/04/2024 a 31/05/2024
    url = "https://archive-api.open-meteo.com/v1/archive?latitude=-30.0332&longitude=-51.2300&start_date=2024-04-01&end_date=2024-05-31&daily=precipitation_sum,rain_sum&timezone=America%2FSao_Paulo"

    try:
        # Adicionado timeout de 15s para evitar travamento da requisição
        res = requests.get(url, timeout=15)
        res.raise_for_status() # Levanta exceção para códigos HTTP de erro (4xx, 5xx)
        return jsonify(res.json())
    except requests.exceptions.RequestException as e:
        # Tratamento de erro rigoroso para falhas na API externa
        return jsonify({"erro": "Falha ao comunicar com Open-Meteo", "detalhes": str(e)}), 502

if __name__ == "__main__":
    app.run(port=5001, debug=True)
