import requests
import json
import logging

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
        url = f'http://{node}{endpoint}'
        try:
            # POST रिक्वेस्ट भेजकर डेटा प्रसारित करें
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
    
    # हम ट्रांजैक्शन को खुद से भेज रहे हैं, इसलिए नोड की सूची में 
    # self.node_address को बाहर करना सुनिश्चित करें।
    
    nodes_to_broadcast = blockchain_instance.nodes.copy()
    
    logging.info(f"P2P: Broadcasting new transaction to {len(nodes_to_broadcast)} nodes.")
    
    broadcast_data(nodes_to_broadcast, endpoint, transaction)


def broadcast_new_block(blockchain_instance, block):
    """
    नेटवर्क को सूचित करता है कि एक नया ब्लॉक सफलतापूर्वक माइन हो गया है।
    """
    # हम एक नया एंडपॉइंट /blocks/new का उपयोग करेंगे जिसे हम node_api.py में जोड़ेंगे।
    endpoint = '/blocks/new'
    
    data = {
        'block': block
    }
    
    nodes_to_broadcast = blockchain_instance.nodes.copy()
    
    logging.info(f"P2P: Broadcasting new block {block['index']} to {len(nodes_to_broadcast)} nodes.")
    
    broadcast_data(nodes_to_broadcast, endpoint, data)