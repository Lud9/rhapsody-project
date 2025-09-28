"""
Flask API Server for RHAPSODY Algorithm
Author: Ludjina
Description: REST API endpoints for running RHAPSODY algorithm and evaluating policies
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import pandas as pd
from werkzeug.utils import secure_filename
import threading
import time

# Import our custom modules
from rhapsody_algorithm import RhapsodyAlgorithm
from policy_evaluator import PolicyEvaluator

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'csv', 'txt'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Global variables to store algorithm state
rhapsody_instance = None
policy_evaluator = None
mining_status = {
    'is_running': False,
    'progress': 0,
    'stage': '',
    'message': '',
    'complete': False,
    'error': None
}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def reset_mining_status():
    """Reset mining status to initial state"""
    global mining_status
    mining_status = {
        'is_running': False,
        'progress': 0,
        'stage': '',
        'message': '',
        'complete': False,
        'error': None
    }


def update_mining_status(progress, stage, message):
    """Update mining status"""
    global mining_status
    mining_status.update({
        'progress': progress,
        'stage': stage,
        'message': message
    })


def run_rhapsody_mining(data_path, T, K, selected_columns):
    """Run RHAPSODY mining in a separate thread"""
    global rhapsody_instance, policy_evaluator, mining_status
    
    try:
        mining_status['is_running'] = True
        mining_status['stage'] = 'Loading data'
        mining_status['progress'] = 10
        
        # Initialize algorithm
        update_mining_status(10, 'Initializing', 'Loading data and initializing algorithm...')
        rhapsody_instance = RhapsodyAlgorithm(selected_columns=selected_columns)
        
        if not rhapsody_instance.load_data(data_path):
            raise Exception("Failed to load data")
        
        mining_status['stage'] = 'Preprocessing data'
        mining_status['progress'] = 20
        mining_status['message'] = f'Processing {len(rhapsody_instance.data)} rows with {len(selected_columns)} columns'

        # Stage 1
        update_mining_status(25, 'Stage 1', 'Computing frequent rules...')
        time.sleep(1)  # Simulate processing time
        
        # Stage 2
        update_mining_status(50, 'Stage 2', 'Computing reliable rules...')
        time.sleep(1)  # Simulate processing time
        
        # Stage 3
        update_mining_status(75, 'Stage 3', 'Removing redundant rules...')
        time.sleep(1)  # Simulate processing time
        
        # Run the algorithm
        final_rules, nUP, nA = rhapsody_instance.run_algorithm(T, K)
        
        # Initialize policy evaluator with results
        policy_evaluator = PolicyEvaluator(final_rules)
        policy_evaluator.rule_statistics = {'nUP': nUP, 'nA': nA}

        policy_evaluator.set_available_attributes(selected_columns)
        
        # Save results
        results_file = os.path.join(app.config['RESULTS_FOLDER'], 'latest_results.json')
        rhapsody_instance.save_results(results_file)
        
        update_mining_status(100, 'Complete', f'Mining complete! Found {len(final_rules)} rules.')
        mining_status['complete'] = True
        mining_status['is_running'] = False
        
    except Exception as e:
        mining_status['error'] = str(e)
        mining_status['is_running'] = False
        print(f"Mining error: {e}")


@app.route('/')
def index():
    """Serve the main page"""
    return jsonify({
        'message': 'RHAPSODY API Server',
        'version': '1.0',
        'endpoints': [
            '/api/upload',
            '/api/mine',
            '/api/status',
            '/api/rules',
            '/api/evaluate',
            '/api/reset'
        ]
    })


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload CSV data file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Read and analyze CSV structure
            try:
                df = pd.read_csv(filepath)
                
                # Get all columns
                columns = list(df.columns)
                ### ###################################################MAY NEED TO BE CHANGED, FROM 100 TO....
                # Get unique values for each column (limit to reasonable size)
                column_values = {}
                for col in columns:
                    unique_vals = df[col].dropna().unique()
                    # Limit to 100 unique values per column to avoid huge responses
                    if len(unique_vals) <= 100:
                        column_values[col] = sorted([str(val) for val in unique_vals])
                    else:
                        # For columns with too many unique values, provide a sample
                        sample_vals = unique_vals[:100]
                        column_values[col] = sorted([str(val) for val in sample_vals])
                
                return jsonify({
                    'message': 'File uploaded successfully',
                    'filename': filename,
                    'rows': len(df),
                    'columns': columns,
                    'column_values': column_values
                })
                
            except Exception as e:
                return jsonify({'error': f'Invalid CSV file: {str(e)}'}), 400
        
        return jsonify({'error': 'File type not allowed'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mine', methods=['POST'])
def start_mining():
    """Start RHAPSODY mining process"""
    try:
        if mining_status['is_running']:
            return jsonify({'error': 'Mining already in progress'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No parameters provided'}), 400
        
        # Get parameters
        filename = data.get('filename')
        T = data.get('T', 20)
        K = data.get('K', 0.5)
        selected_columns = data.get('selected_columns', [])  # NEW
        
        if not filename:
            return jsonify({'error': 'Filename required'}), 400
        
        if not selected_columns:
            return jsonify({'error': 'Selected columns required'}), 400
        
        # Check if file exists
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Validate selected columns exist in the file
        try:
            df = pd.read_csv(filepath)
            missing_cols = [col for col in selected_columns if col not in df.columns]
            if missing_cols:
                return jsonify({'error': f'Selected columns not found in file: {missing_cols}'}), 400
        except Exception as e:
            return jsonify({'error': f'Error reading file: {str(e)}'}), 400
        
        # Reset status and start mining in background thread
        reset_mining_status()
        mining_thread = threading.Thread(
            target=run_rhapsody_mining,
            args=(filepath, int(T), float(K), selected_columns)  # Pass selected columns
        )
        mining_thread.daemon = True
        mining_thread.start()
        
        return jsonify({
            'message': 'Mining started successfully',
            'parameters': {'T': T, 'K': K, 'filename': filename, 'selected_columns': selected_columns}
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_mining_status():
    """Get current mining status"""
    return jsonify(mining_status)


@app.route('/api/rules', methods=['GET'])
def get_rules():
    """Get mined rules"""
    try:
        if not rhapsody_instance or not mining_status['complete']:
            return jsonify({'error': 'No rules available. Complete mining first.'}), 400
        
        stats = rhapsody_instance.get_rule_statistics()
        
        return jsonify({
            'rules': stats['rules']['final'],
            'statistics': {
                'total_transactions': stats['total_transactions'],
                'frequent_rules': stats['frequent_rules_count'],
                'reliable_rules': stats['reliable_rules_count'],
                'final_rules': stats['final_rules_count']
            },
            'nUP': stats['nUP'],
            'nA': stats['nA']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/attributes', methods=['GET'])
def get_available_attributes():
    """Get available attributes from mined rules"""
    try:
        if not policy_evaluator or not mining_status['complete']:
            return jsonify({'error': 'No policies available. Complete mining first.'}), 400
        
        attributes = policy_evaluator.get_available_attributes()
        
        return jsonify({
            'attributes': attributes,
            'count': len(attributes)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/evaluate', methods=['POST'])
def evaluate_request():
    """Evaluate access request against mined policies"""
    try:
        if not policy_evaluator or not mining_status['complete']:
            return jsonify({'error': 'No policies available. Complete mining first.'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No request data provided'}), 400
        
        # Create access request
        # Get available attributes from policy evaluator
        available_attrs = policy_evaluator.get_available_attributes()

        # Create access request with only available attributes
        access_request = {}
        for attr in available_attrs:
            if attr in data:
                access_request[attr] = data.get(attr, '')
        
        # Evaluate request
        result = policy_evaluator.evaluate_request(access_request)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/batch_evaluate', methods=['POST'])
def batch_evaluate():
    """Evaluate multiple access requests"""
    try:
        if not policy_evaluator or not mining_status['complete']:
            return jsonify({'error': 'No policies available. Complete mining first.'}), 400
        
        data = request.get_json()
        if not data or 'requests' not in data:
            return jsonify({'error': 'No requests provided'}), 400
        
        requests = data['requests']
        available_attrs = policy_evaluator.get_available_attributes()
        filtered_requests = []
        for req in requests:
            filtered_req = {attr: req.get(attr, '') for attr in available_attrs if attr in req}
            filtered_requests.append(filtered_req)

        results = policy_evaluator.batch_evaluate(filtered_requests)
        
        # Calculate summary statistics
        granted_count = sum(1 for r in results if r['granted'])
        denied_count = len(results) - granted_count
        
        return jsonify({
            'results': results,
            'summary': {
                'total': len(results),
                'granted': granted_count,
                'denied': denied_count,
                'grant_rate': granted_count / len(results) if results else 0
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate_test_requests', methods=['GET'])
def generate_test_requests():
    """Generate test requests based on mined rules"""
    try:
        if not policy_evaluator or not mining_status['complete']:
            return jsonify({'error': 'No policies available. Complete mining first.'}), 400
        
        num_requests = request.args.get('count', 10, type=int)
        test_requests = policy_evaluator.generate_test_requests(num_requests)
        
        return jsonify({
            'test_requests': test_requests,
            'count': len(test_requests)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rule_statistics', methods=['GET'])
def get_rule_statistics():
    """Get detailed rule statistics and coverage information"""
    try:
        if not policy_evaluator or not mining_status['complete']:
            return jsonify({'error': 'No policies available. Complete mining first.'}), 400
        
        stats = policy_evaluator.get_rule_coverage_stats()
        conflicts = policy_evaluator.find_conflicting_rules()
        
        return jsonify({
            'coverage_stats': stats,
            'conflicting_rules': conflicts,
            'conflict_count': len(conflicts)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export_report', methods=['POST'])
def export_evaluation_report():
    """Export comprehensive evaluation report"""
    try:
        if not policy_evaluator or not mining_status['complete']:
            return jsonify({'error': 'No policies available. Complete mining first.'}), 400
        
        data = request.get_json()
        requests = data.get('requests', [])
        
        if not requests:
            # Generate sample requests if none provided
            requests = policy_evaluator.generate_test_requests(20)
        
        # Generate report
        report_file = os.path.join(app.config['RESULTS_FOLDER'], 'evaluation_report.json')
        report = policy_evaluator.export_evaluation_report(requests, report_file)
        
        return jsonify({
            'message': 'Report generated successfully',
            'report_file': 'evaluation_report.json',
            'summary': report['evaluation_summary']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def reset_system():
    """Reset the system state"""
    global rhapsody_instance, policy_evaluator
    
    try:
        if mining_status['is_running']:
            return jsonify({'error': 'Cannot reset while mining is in progress'}), 400
        
        # Reset global variables
        rhapsody_instance = None
        policy_evaluator = None
        reset_mining_status()
        
        return jsonify({'message': 'System reset successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download result files"""
    try:
        return send_from_directory(app.config['RESULTS_FOLDER'], filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large'}), 413


if __name__ == '__main__':
    print("Starting RHAPSODY API Server...")
    print("Available endpoints:")
    print("  POST /api/upload - Upload CSV data file")
    print("  POST /api/mine - Start mining process")
    print("  GET  /api/status - Get mining status")
    print("  GET  /api/rules - Get mined rules")
    print("  POST /api/evaluate - Evaluate single access request")
    print("  POST /api/batch_evaluate - Evaluate multiple requests")
    print("  GET  /api/generate_test_requests - Generate test requests")
    print("  GET  /api/rule_statistics - Get rule statistics")
    print("  POST /api/export_report - Export evaluation report")
    print("  POST /api/reset - Reset system state")
    print("  GET  /api/download/<filename> - Download result files")
    
    app.run(debug=True, host='0.0.0.0', port=5000)