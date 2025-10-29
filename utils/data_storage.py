import json
import os

# डेटा फ़ाइल का नाम
DATA_FILE = 'blockchain.json'
# डेटा को प्रोजेक्ट रूट में 'data/' फ़ोल्डर में सेव करें
DATA_PATH = os.path.join('data', DATA_FILE)

def ensure_data_directory():
    """ सुनिश्चित करता है कि डेटा फ़ोल्डर मौजूद है """
    data_dir = os.path.dirname(DATA_PATH)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created data directory: {data_dir}")

def save_blockchain(chain_data, current_difficulty, current_nodes):
    """
    ब्लॉकचेन चेन, कठिनाई, और नोड लिस्ट को डिस्क पर JSON फ़ाइल में सेव करता है।
    """
    ensure_data_directory()
    
    data_to_save = {
        'chain': chain_data,
        'difficulty': current_difficulty,
        # नोड सेट को लिस्ट में बदलें क्योंकि JSON सेट को सेव नहीं कर सकता
        'nodes': list(current_nodes), 
        'timestamp': os.path.getmtime(os.path.dirname(DATA_PATH))
    }
    
    try:
        with open(DATA_PATH, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        print(f"\n✅ Blockchain data successfully saved to {DATA_PATH}")
    except Exception as e:
        print(f"\n❌ Error saving blockchain data: {e}")

def load_blockchain():
    """
    डिस्क से ब्लॉकचेन डेटा लोड करता है। (पुराने फॉर्मेट में)
    यदि फ़ाइल मौजूद नहीं है, तो None रिटर्न करता है।
    """
    if not os.path.exists(DATA_PATH):
        print(f"\n💡 Data file not found at {DATA_PATH}. Starting with Genesis Block.")
        return None

    try:
        with open(DATA_PATH, 'r') as f:
            data = json.load(f)
            print(f"\n✅ Blockchain data loaded successfully from {DATA_PATH}")
            # नोड लिस्ट को वापस सेट में बदलें
            data['nodes'] = set(data.get('nodes', [])) 
            return data
    except Exception as e:
        print(f"\n❌ Error loading blockchain data. Starting fresh. Error: {e}")
        return None

# --------------------------------------------------------------------------
# 🆕 P2P के लिए नया फ़ंक्शन (Gunicorn Worker Compatibility)
# --------------------------------------------------------------------------

def load_blockchain_data():
    """ 
    चेन, कठिनाई, और नोड लिस्ट को एक टपल के रूप में लोड करता है।
    यह Gunicorn वर्कर्स द्वारा P2P नोड लिस्ट को रीलोड करने के लिए आवश्यक है।
    """
    if not os.path.exists(DATA_PATH):
        # अगर फाइल नहीं मिली, तो डिफॉल्ट मान रिटर्न करें
        return [], 4, set() 

    try:
        with open(DATA_PATH, 'r') as f:
            data = json.load(f)
            
        # चेन, कठिनाई, और नोड लिस्ट को अलग-अलग रिटर्न करें
        chain = data.get('chain', [])
        difficulty = data.get('difficulty', 4)
        # नोड सेट को कनवर्ट करें
        nodes = set(data.get('nodes', [])) 

        return chain, difficulty, nodes
        
    except Exception:
        # कुछ अन्य त्रुटि होने पर डिफॉल्ट मान रिटर्न करें
        return [], 4, set()
