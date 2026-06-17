from flask import jsonify

def handle_404(error):
    return jsonify({'error': 'Not found'}), 404

def handle_500(error):
    return jsonify({'error': 'Internal server error'}), 500

def handle_403(error):
    return jsonify({'error': 'Forbidden'}), 403
