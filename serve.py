from flask import Flask, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory('.', filename, conditional=True)

if __name__ == '__main__':
    print("Serving at http://localhost:8080")
    app.run(port=8080, debug=False)
