from flask import Flask, jsonify, request, render_template # render_template जोड़ा गया
from uuid import uuid4
import os 
import requests 

# मुख्य कोर लॉजिक को कोर डायरेक्टरी से इंपोर्ट करें
from core.blockchain import Blockchain 
# Persistence (Node List Saving) के लिए आवश्यक
from utils.data_storage import save_blockchain 
 

# ----------------------------------------------------
# 1. API और नोड सेटअप
# ----------------------------------------------------

# Flask App शुरू करें
app = Flask(__name__)

# इस नोड के लिए एक अद्वितीय ID बनाएँ 
node_identifier = str(uuid4()).replace('-', '')

# Blockchain क्लास शुरू करें (यह Persistence के कारण डेटा लोड करेगी)
blockchain = Blockchain(node_address=node_identifier)

# ----------------------------------------------------
# 2. UI रेंडरिंग एंडपॉइंट (नया/अपडेटेड)
# ----------------------------------------------------

# मुख्य वेब UI एंडपॉइंट
@app.route('/', methods=['GET'])
def index():
    """ 
    वेब UI (index.html) को रेंडर करता है और नोड का पता पास करता है।
    """
    # templates/index.html को रेंडर करें
    return render_template('index.html', node_id=node_identifier)


# ----------------------------------------------------
# 3. ब्लॉकचेन ऑपरेशन एंडपॉइंट्स
# ----------------------------------------------------

# माइनिंग एंडपॉइंट
@app.route('/mine', methods=['GET'])
def mine():
    """ 
    एक नया ब्लॉक माइन करता है। 
    नोट: broadcast_new_block() कॉल blockchain.py में है।
    """
    # 1. अगला प्रूफ-ऑफ-वर्क खोजें
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # 2. रिवॉर्ड और नया ब्लॉक बनाएँ
    previous_hash = blockchain.hash(last_block)
    
    # यह कॉल ब्लॉक को चेन में जोड़ती है, डिस्क पर सेव करती है, और P2P पर प्रसारित करती है।
    block = blockchain.new_block(
        proof=proof, 
        previous_hash=previous_hash, 
        miner_address=node_identifier 
    )

    response = {
        'message': "नया ब्लॉक सफलतापूर्वक माइन हो गया और नेटवर्क पर प्रसारित हो गया!",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
        'reward': block['transactions'][0]['amount'] 
    }
    return jsonify(response), 200

# नया ट्रांजैक्शन एंडपॉइंट
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    """ 
    मेमोरी पूल में एक नया ट्रांजैक्शन जोड़ता है। 
    प्रसारण (Broadcasting) लॉजिक blockchain.py में है।
    """
    values = request.get_json()

    required = ['sender', 'recipient', 'amount', 'signature']
    if not all(k in values for k in required):
        return 'Missing required values: sender, recipient, amount, signature', 400

    # new_transaction() में हस्ताक्षर, बैलेंस और प्रसारण की जाँच होती है
    index, message = blockchain.new_transaction(
        values['sender'], 
        values['recipient'], 
        values['amount'],
        values['signature']
    )
    
    if index is False:
        return jsonify({'message': message}), 406 

    response = {'message': f'ट्रांजैक्शन सफलतापूर्वक पूल में जोड़ा गया और नेटवर्क पर प्रसारित हो गया।'}
    return jsonify(response), 201

# पूरी चेन दिखाने का एंडपॉइंट
@app.route('/chain', methods=['GET'])
def full_chain():
    """ पूरी ब्लॉकचेन को रिटर्न करता है (सर्वसम्मति द्वारा उपयोग किया जाता है) """
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
        'difficulty': blockchain.difficulty
    }
    return jsonify(response), 200

# बैलेंस एंडपॉइंट
@app.route('/balance/<address>', methods=['GET'])
def get_address_balance(address):
    """ किसी दिए गए पते का वर्तमान बैलेंस रिटर्न करता है। """
    balance = blockchain.balance_manager.get_balance(address)
    
    response = {
        'address': address,
        'balance': balance,
        'message': 'Balance retrieved successfully'
    }
    return jsonify(response), 200


# ----------------------------------------------------
# 4. P2P और नेटवर्क प्रबंधन एंडपॉइंट्स
# ----------------------------------------------------

# नया ब्लॉक प्राप्त करने के लिए एंडपॉइंट (P2P द्वारा उपयोग किया जाता है)
@app.route('/blocks/new', methods=['POST'])
def receive_new_block():
    """
    नेटवर्क से एक नया ब्लॉक प्राप्त करें और सर्वसम्मति (Consensus) द्वारा 
    अपनी चेन को अपडेट करने का प्रयास करें।
    """
    values = request.get_json()
    block = values.get('block')

    if block is None:
        return jsonify({'message': 'Error: Missing block data'}), 400
    
    # P2P से प्राप्त ब्लॉक को प्रोसेस करने का सबसे आसान और सुरक्षित तरीका सर्वसम्मति चलाना है।
    # यह सुनिश्चित करता है कि प्राप्त ब्लॉक वैध है और सबसे लंबी चेन का हिस्सा है।
    replaced = blockchain.resolve_conflicts() 

    if replaced:
        return jsonify({'message': 'New block received, chain updated via consensus.'}), 200
    else:
        # यदि बदला नहीं गया, तो इसका मतलब है कि या तो प्राप्त ब्लॉक छोटा है, 
        # या हमारी चेन पहले से ही नवीनतम है।
        return jsonify({'message': 'New block received, but local chain is authoritative or block is old.'}), 200


# अन्य नोड्स को रजिस्टर करने का एंडपॉइंट
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    """ अन्य नोड्स को अपने नोड लिस्ट में जोड़ता है और नोड लिस्ट को डिस्क पर सेव करता है। """
    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)
        
    # नोड लिस्ट को डिस्क पर सेव करें (Persistence)
    save_blockchain(blockchain.chain, blockchain.difficulty, blockchain.nodes)


    response = {
        'message': 'नए नोड्स जोड़ दिए गए हैं',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

# सर्वसम्मति (Consensus) एंडपॉइंट
@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    """ सबसे लंबी और वैध चेन के लिए बलपूर्वक जाँच करता है। """
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'चेन को सबसे लंबी, वैध चेन से बदल दिया गया',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'हमारी चेन आधिकारिक (authoritative) है',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


# ----------------------------------------------------
# 5. App चलाना (Execution)
# ----------------------------------------------------

if __name__ == '__main__':
    # यह खंड केवल सीधी टेस्टिंग के लिए है। 
    # मुख्य नोड को चलाने के लिए 'blockchain_app.py' का उपयोग करें।
    port = os.environ.get('PORT', 5000)
    app.run(host='0.0.0.0', port=port)
