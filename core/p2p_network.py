import requests
import json
import logging

# यह इंपोर्ट जोड़ें (या सुनिश्चित करें कि यह utils/data_storage में मौजूद है)
from utils.data_storage import load_blockchain_data 

# नेटवर्क गतिविधि को ट्रैक करने के लिए लॉगिंग सेट करें
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def broadcast_data(node_set, endpoint, data):
    """
    नेटवर्क में सभी रजिस्टर्ड नोड्स को दिए गए एंडपॉइंट पर डेटा भेजता है।
    """
    success_count = 0
    
    # सुनिश्चित करें कि node_set एक सेट है
    if not isinstance(node_set, set):
        logging.error("P2P: Invalid node list provided (expected set).")
        return success_count

    # प्रत्येक पड़ोसी नोड पर लूप करें
    for node in node_set:
        # Render URL HTTPS का उपयोग करते हैं। 
        # http:// या https:// में से सही चुनें
        # हम यहाँ सुरक्षा के लिए HTTPS मान रहे हैं, लेकिन Render के आंतरिक कम्युनिकेशन के लिए HTTP का भी प्रयास कर सकते हैं।
        url = f'http://{node}{endpoint}' 
        try:
            # POST रिक्वेस्ट भेजकर डेटा प्रसारित करें
            # 5 सेकंड का टाइमआउट सेट किया गया
            response = requests.post(url, json=data, timeout=5)
            
            if response.status_code in [200, 201]:
                success_count += 1
                # logging.info(f"P2P: Successfully broadcast to {node}{endpoint}")
            else:
                logging.warning(f"P2P: Failed to broadcast to {node}. Status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            # कनेक्शन त्रुटियों को पकड़ें (जैसे नोड ऑफ़लाइन है)
            logging.error(f"P2P: Node {node} is unreachable. Error: {e}")
            
    return success_count

def broadcast_transaction(blockchain_instance, transaction):
    """
    एक नए ट्रांजैक्शन को सभी नोड्स पर प्रसारित करता है।
    """
    # /transactions/new एंडपॉइंट का उपयोग करें
    endpoint = '/transactions/new'
    
    # ट्रांजैक्शन पूल के लिए भी ताज़ा नोड लिस्ट का उपयोग करना बेहतर है।
    try:
        _, _, nodes_to_broadcast = load_blockchain_data()
    except Exception:
        # यदि डिस्क से लोड नहीं हो सका, तो मेमोरी में मौजूद का उपयोग करें
        nodes_to_broadcast = blockchain_instance.nodes.copy()
    
    logging.info(f"P2P: Broadcasting new transaction to {len(nodes_to_broadcast)} nodes.")
    
    broadcast_data(nodes_to_broadcast, endpoint, transaction)


def broadcast_new_block(blockchain_instance, block):
    """
    नेटवर्क को सूचित करता है कि एक नया ब्लॉक सफलतापूर्वक माइन हो गया है।
    🚨 Gunicorn अनुकूलता के लिए यहाँ नोड लिस्ट को डिस्क से रीलोड किया गया है।
    """
    endpoint = '/blocks/new'
    
    data = {
        'block': block
    }
    
    # 🚨 महत्वपूर्ण सुधार: नोड लिस्ट को डिस्क से रीलोड करें 
    # (ताकि Gunicorn वर्कर ताज़ा डेटा उपयोग करें)
    try:
        # load_blockchain_data को चेन, कठिनाई और नोड्स को रिटर्न करना चाहिए।
        _, _, nodes_to_broadcast = load_blockchain_data()
    except Exception as e:
        logging.warning(f"P2P: Failed to load fresh node list from disk: {e}. Using current memory list.")
        # यदि डिस्क से लोड नहीं हो सका, तो मेमोरी में मौजूद का उपयोग करें
        nodes_to_broadcast = blockchain_instance.nodes.copy()
        
    logging.info(f"P2P: Broadcasting new block {block['index']} to {len(nodes_to_broadcast)} nodes.")
    
    success_count = broadcast_data(nodes_to_broadcast, endpoint, data)
    
    # यह सुनिश्चित करने के लिए कि लॉग सही हो, सफल प्रसारण की संख्या का उपयोग करें
    logging.info(f"P2P: Successfully broadcast block {block['index']} to {success_count} nodes.")
