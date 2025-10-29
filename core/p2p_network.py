import requests
import json
from typing import TYPE_CHECKING, Dict, Any, Set

# Gunicorn वर्कर अनुकूलता के लिए data_storage से इंपोर्ट करें
from utils.data_storage import load_blockchain_data 

# Circular dependency से बचने के लिए
if TYPE_CHECKING:
    from .blockchain import Blockchain 
else:
    # यदि आप type checking नहीं कर रहे हैं, तो Placeholder का उपयोग करें
    Blockchain = Any


def broadcast_transaction(blockchain: 'Blockchain', transaction: Dict[str, Any]):
    """ एक नए ट्रांजैक्शन को नेटवर्क में प्रसारित करता है। """
    
    # ट्रांजैक्शन प्रसारण के लिए भी नोड लिस्ट रीलोड करें 
    try:
        _, _, fresh_nodes = load_blockchain_data()
        nodes_to_broadcast = fresh_nodes
    except Exception:
        nodes_to_broadcast = blockchain.nodes

    for node in nodes_to_broadcast:
        # P2P URLs को सही करें
        url = f'https://{node}/transactions/new' if 'http' not in node and 'https' not in node else f'{node}/transactions/new'
        
        try:
            requests.post(url, json=transaction, timeout=2) 
        except requests.exceptions.RequestException:
            # प्रसारण विफल रहा, अगले नोड पर जाएँ
            continue


def broadcast_new_block(blockchain: 'Blockchain', block: Dict[str, Any]):
    """ 
    नए ब्लॉक को नेटवर्क में सभी नोड्स तक प्रसारित (broadcast) करता है।
    """
    
    # 🚨 महत्वपूर्ण सुधार: नोड लिस्ट को डिस्क से रीलोड करें 
    successful_transmissions = 0
    
    try:
        _, _, fresh_nodes = load_blockchain_data()
        nodes_to_broadcast: Set[str] = fresh_nodes
        
    except Exception as e:
        print(f"ERROR: Could not load fresh nodes for broadcast: {e}")
        nodes_to_broadcast = blockchain.nodes
        
    # डिस्क से रीलोड की गई नोड लिस्ट पर प्रसारण करें
    for node in nodes_to_broadcast:
        # P2P URLs को सही करें
        url = f'https://{node}/blocks/new' if 'http' not in node and 'https' not in node else f'{node}/blocks/new'

        try:
            response = requests.post(url, json={'block': block}, timeout=3) 
            
            if response.status_code == 200 or response.status_code == 201:
                successful_transmissions += 1
            else:
                print(f"WARN: Could not broadcast block to {node}. Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            # print(f"ERROR: Failed to broadcast block to {node}. Error: {e}")
            pass # विफल नोड्स के लिए लॉग को शांत रखें

    print(f"P2P: Broadcasting new block {block['index']} to {successful_transmissions} nodes.")
    return successful_transmissions
