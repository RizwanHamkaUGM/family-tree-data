from flask import Flask, request, jsonify, send_file
from graphviz import Digraph
import os
from firebase_admin import credentials, initialize_app, db
from flask_cors import CORS
import json
from base64 import b64encode

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

firebase_credentials = os.getenv('FIREBASE_CREDENTIALS')
cred_dict = json.loads(firebase_credentials)
cred = credentials.Certificate(cred_dict)
initialize_app(cred, {"databaseURL": "https://silsilah-keluarga-10d90-default-rtdb.firebaseio.com/"})

STATIC_FOLDER = "/tmp"
os.makedirs(STATIC_FOLDER, exist_ok=True)

def load_data():
    """Memuat data keluarga dari Firebase."""
    ref = db.reference("family")
    family_data = ref.get()
    return {"family": family_data} if family_data else {"family": []}

def save_data(data):
    """Menyimpan data keluarga ke Firebase."""
    ref = db.reference("family")
    ref.set(data["family"])

def generate_family_tree_base64(family):
    """Menghasilkan silsilah keluarga dalam format base64 menggunakan Graphviz."""
    graph = Digraph(format="png")
    graph.attr(rankdir="TB")

    # Tambahkan node untuk setiap anggota keluarga
    for member in family:
        graph.node(
            str(member["id"]),
            label=f'{member["name"]}\n({member.get("anggota", "")})',
            shape="box",
        )

    # Tambahkan edge untuk hubungan orang tua-anak
    for member in family:
        if "parent1_id" in member and member["parent1_id"]:
            graph.edge(str(member["parent1_id"]), str(member["id"]))
        if "parent2_id" in member and member["parent2_id"]:
            graph.edge(str(member["parent2_id"]), str(member["id"]))

    # Simpan file di direktori /tmp
    output_path = "/tmp/family_tree"
    graph.render(output_path, format="png", cleanup=True)

    # Encode file menjadi Base64
    with open(f"{output_path}.png", "rb") as f:
        encoded_image = b64encode(f.read()).decode('utf-8')

    return encoded_image

@app.route("/family", methods=["GET"])
def get_family():
    """Mengembalikan data keluarga."""
    data = load_data()
    return jsonify(data)

@app.route("/family/tree", methods=["GET"])
def family_tree():
    """Mengembalikan gambar silsilah keluarga dalam format Base64."""
    try:
        data = load_data()["family"]
        image_base64 = generate_family_tree_base64(data)
        return jsonify({"image": image_base64})
    except Exception as e:
        app.logger.error(f"Error generating family tree: {e}")
        return jsonify({"error": "Failed to generate family tree"}), 500

@app.route("/family", methods=["POST"])
def add_family_member():
    """Menambahkan anggota keluarga baru."""
    data = load_data()
    new_member = request.json

    # Validasi properti wajib
    required_fields = ["id", "name", "anggota"]
    for field in required_fields:
        if field not in new_member:
            return jsonify({"error": f"Field '{field}' is required"}), 400

    # Tambahkan properti opsional jika tidak ada
    new_member.setdefault("parent1_id", None)
    new_member.setdefault("parent2_id", None)

    data["family"].append(new_member)
    save_data(data)
    return jsonify({"message": "Member added successfully"}), 201

if __name__ == "__main__":
    app.run(debug=True)
