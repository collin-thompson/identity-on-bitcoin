#!/usr/bin/python
from bitcoin.pyspecials import *
import json, re
import random
import sys
try:
    from urllib.request import build_opener
except:
    from urllib2 import build_opener

BCI_API = ""
CHAIN_API = "api-key-id=211a589ce9bbc35de662ee02d51aa860"
BITEASY_API = ""

def set_api(*args):
    """Set API code for web service"""
    # "api_hex_code_string", "service" or defaults to "bci"
    if len(args)==2 and args[1] in ("bci", "chain"):
        code, svc = args[0], args[1]
    else:
        code, svc = args[0], "bci"
    if svc == "bci":
        global BCI_API
        BCI_API = code
    if svc == "chain":
        global CHAIN_API
        CHAIN_API = code

# Makes a request to a given URL (first arg) and optional params (second arg)
def make_request(*args):
    opener = build_opener()
    opener.addheaders = [('User-agent',
                          'Mozilla/5.0'+str(random.randrange(1000000)))]
    try:
        return st(opener.open(*args).read().strip()) # st returns a string, NOT bytestring
    except Exception as e:
        try:
            p = st(e.read().strip())
        except:
            p = e
        raise Exception(p)


def parse_addr_args(*args):
    # Valid input formats: blockr_unspent([addr1, addr2,addr3])
    #                      blockr_unspent(addr1, addr2, addr3)
    #                      blockr_unspent([addr1, addr2, addr3], network)
    #                      blockr_unspent(addr1, addr2, addr3, network)
    # Where network is 'btc' or 'testnet'
    network = 'btc'
    addr_args = args
    if len(args) >= 1 and args[-1] in ('testnet', 'btc'):
        network = args[-1]
        addr_args = args[:-1]
    if len(addr_args) == 1 and isinstance(addr_args, list):
        addr_args = addr_args[0]

    return network, addr_args


# Gets the unspent outputs of one or more addresses
def bci_unspent(*args, **kwargs):
    api = "?api=%s" % BCI_API if BCI_API else ""
    network, addrs = parse_addr_args(*args)
    u = []
    for a in addrs:
        try:
            data = make_request('https://blockchain.info/unspent?address=%s%s' % (a, api))
        except Exception as e:
            if str(e) == 'No free outputs to spend':
                continue
            else:
                raise Exception(e)
        try:
            jsonobj = json.loads(data)
            for o in jsonobj["unspent_outputs"]:
                h = hexify(unhexify(o['tx_hash'])[::-1])
                u.append({
                    "output": h+':'+str(o['tx_output_n']),
                    "value": o['value']
                })
        except:
            raise Exception("Failed to decode data: "+data)
    return u


def blockr_unspent(*args):
    # Valid input formats: blockr_unspent([addr1, addr2,addr3])
    #                      blockr_unspent(addr1, addr2, addr3)
    #                      blockr_unspent([addr1, addr2, addr3], network)
    #                      blockr_unspent(addr1, addr2, addr3, network)
    # Where network is 'btc' or 'testnet'
    network, addr_args = parse_addr_args(*args)

    if network == 'testnet':
        blockr_url = 'http://tbtc.blockr.io/api/v1/address/unspent/'
    elif network == 'btc':
        blockr_url = 'http://btc.blockr.io/api/v1/address/unspent/'
    else:
        raise Exception(
            'Unsupported network {0} for blockr_unspent'.format(network))

    if len(addr_args) == 0:
        return []
    elif isinstance(addr_args[0], list):
        addrs = addr_args[0]
    else:
        addrs = addr_args
    res = make_request(blockr_url+','.join(addrs))
    data = json.loads(res)['data']
    o = []
    if 'unspent' in data:
        data = [data]
    for dat in data:
        for u in dat['unspent']:
            o.append({
                "output": u['tx']+':'+str(u['n']),
                "value": int(u['amount'].replace('.', ''))
            })
    return o


def helloblock_unspent(*args):
    network, addrs = parse_addr_args(*args)
    if network == 'testnet':
        url = 'https://testnet.helloblock.io/v1/addresses/%s/unspents?limit=500&offset=%s'
    elif network == 'btc':
        url = 'https://mainnet.helloblock.io/v1/addresses/%s/unspents?limit=500&offset=%s'
    o = []
    for addr in addrs:
        for offset in xrange(0, 10**9, 500):
            res = make_request(url % (addr, offset))
            data = json.loads(res)["data"]
            if not len(data["unspents"]):
                break
            elif offset:
                sys.stderr.write("Getting more unspents: %d\n" % offset)
            for dat in data["unspents"]:
                o.append({
                    "output": dat["txHash"]+':'+str(dat["index"]),
                    "value": dat["value"],
                })
    return o

def biteasy_unspent(*args):
    network, addrs = parse_addr_args(*args)
    base_url = "https://api.biteasy.com/%s/v1/"
    url = base_url % 'testnet' if network == 'testnet' else base_url % "blockchain"
    offset, txs = 0, []
    for addr in addrs:
        # TODO: fix multi address search
        while True:
            data = make_request(url + "/addresses/%s/unspent-outputs?per_page=20" % addr)
            try:
                jsondata = json.loads(data)
            except:
                raise Exception("Could not decode JSON data")
            txs.extend(jsondata['data']['outputs'])
            if jsondata['data']['pagination']['next_page'] is False:
                break
            offset += 20 # jsondata['data']['pagination']["per_page"]
            sys.stderr.write("Fetching more transactions... " + str(offset) + '\n')
        o = []
        for utxo in txs:
            assert utxo['to_address'] == addr and utxo['is_spent'] == 0, "Wrong address or UTXO is spent"
            o.append({
                "output": "%s:%d" % (utxo['transaction_hash'], utxo['transaction_index']),
                "value": utxo['value']
            })
        return o



# def webbtc_unspent(*args):
#     network, addrs = parse_addr_args(*args)
#     if network == 'testnet':
#         url = "http://test.webbtc.com/address/%s.json"
#     elif network == 'btc':
#         url = "http://webbtc.com/address/%s.json"
#     o = []
#     for addr in addrs:
#         mr = make_request(url % addr)
#         if mr['balance'] == 0:
#             break

unspent_getters = {
    'bci': bci_unspent,
    'blockr': blockr_unspent,
    #'webbtc': webbtc_unspent,           # TODO: implement webbtc unspent function
    'helloblock': helloblock_unspent,
    'biteasy': biteasy_unspent
}


def unspent(*args, **kwargs):
    """unspent(addr, "btc", source="blockr")"""
    svc = kwargs.get('source', '')
    f = unspent_getters.get(svc, blockr_unspent)
    return f(*args)


# Gets the transaction output history of a given set of addresses,
# including whether or not they have been spent
def history(*args):
    # Valid input formats: history([addr1, addr2,addr3], "btc")
    #                      history(addr1, addr2, addr3, "testnet")
    if len(args) == 0:
        return []
    elif len(args) == 2 and isinstance(args[0], list):
        addrs, network = args[0], args[-1]
    elif len(args) > 2:
        addrs, network = args[:-1], args[-1]
    else:
        addrs = args
        network = "btc"

    if network == "testnet":
        pass

        # #utxos = []  # using https://api.biteasy.com/blockchain/v1/addresses/_ADDR_/unspent-outputs
        # txs = []    # using https://api.biteasy.com/blockchain/v1/transactions?address=_ADDR_
        # for addr in addrs:
        #     offset = 0
        #     while 1:
        #         gathered = False
        #         while not gathered:
        #             try:
        #                 data = make_request(
        #                     "https://api.biteasy.com/%s/v1/addresses/%s/unspent-outputs" %
        #                     ('testnet', addr))
        #                 gathered = True
        #             except Exception as e:
        #                 try:
        #                     sys.stderr.write(e.read().strip())
        #                 except:
        #                     sys.stderr.write(str(e))
        #                 gathered = False
        #         try:
        #             jsonobj = json.loads(data)
        #         except:
        #             raise Exception("Failed to decode data: " + data)
        #         txs.extend(jsonobj["data"]["transactions"])
        #         if not jsonobj['data']['pagination']['next_page']:
        #             break
        #         offset += 20
        #         sys.stderr.write("Fetching more transactions... " + str(offset) + '\n')
        # outs = {}
        # for tx in txs:
        #     if tx['to_address'] in addrs:
        #         key = str(tx["tx_index"]) + ':' + str(o["n"])
        #         outs[key] = {
        #             "address": o["addr"],
        #             "value": o["value"],
        #             "output": tx["hash"] + ':' + str(o["n"]),
        #             "block_height": tx.get("block_height", None)
        #         }
        # for tx in txs:
        #     for i, inp in enumerate(tx["inputs"]):
        #         if "prev_out" in inp:
        #             if inp["prev_out"]["addr"] in addrs:
        #                 key = str(inp["prev_out"]["tx_index"]) + \
        #                       ':' + str(inp["prev_out"]["n"])
        #                 if outs.get(key):
        #                     outs[key]["spend"] = tx["hash"] + ':' + str(i)
        # return [outs[k] for k in outs]
    elif network == "btc":
        api = "?api=%s" % BCI_API if BCI_API else ""
        txs = []
        for addr in addrs:
            offset = 0
            while 1:
                gathered = False
                while not gathered:
                    try:
                        data = make_request(
                            'https://blockchain.info/address/%s?format=json&offset=%s%s' %
                            (addr, offset, api))
                        gathered = True
                    except Exception as e:
                        try:
                            sys.stderr.write(e.read().strip())
                        except:
                            sys.stderr.write(str(e))
                        gathered = False
                try:
                    jsonobj = json.loads(data)
                except:
                    raise Exception("Failed to decode data: "+data)
                txs.extend(jsonobj["txs"])
                if len(jsonobj["txs"]) < 50:
                    break
                offset += 50
                sys.stderr.write("Fetching more transactions... "+str(offset)+'\n')
        outs = {}
        for tx in txs:
            for o in tx["out"]:
                if o['addr'] in addrs:
                    key = str(tx["tx_index"])+':'+str(o["n"])
                    outs[key] = {
                        "address": o["addr"],
                        "value": o["value"],
                        "output": tx["hash"]+':'+str(o["n"]),
                        "block_height": tx.get("block_height", None)
                    }
        for tx in txs:
            for i, inp in enumerate(tx["inputs"]):
                if "prev_out" in inp:
                    if inp["prev_out"]["addr"] in addrs:
                        key = str(inp["prev_out"]["tx_index"]) + \
                              ':'+str(inp["prev_out"]["n"])
                        if outs.get(key):
                            outs[key]["spend"] = tx["hash"] + ':' + str(i)
        return [outs[k] for k in outs]


# Pushes a transaction to the network using https://blockchain.info/pushtx
def bci_pushtx(tx):
    if not re.match('^[0-9a-fA-F]*$', tx): 
        tx = hexify(tx)
    return make_request('https://blockchain.info/pushtx', 'tx='+tx)


def eligius_pushtx(tx):
    if not re.match('^[0-9a-fA-F]*$', tx): tx = hexify(tx)
    s = make_request(
        'http://eligius.st/~wizkid057/newstats/pushtxn.php',
        'transaction='+tx+'&send=Push')
    strings = re.findall('string[^"]*"[^"]*"', s)
    for string in strings:
        quote = re.findall('"[^"]*"', string)[0]
        if len(quote) >= 5:
            return quote[1:-1]


def blockr_pushtx(tx, network='btc'):
    if network == 'testnet':
        blockr_url = 'http://tbtc.blockr.io/api/v1/tx/push'
    elif network == 'btc':
        blockr_url = 'http://btc.blockr.io/api/v1/tx/push'
    else:
        raise Exception(
            'Unsupported network {0} for blockr_pushtx'.format(network))

    if not re.match('^[0-9a-fA-F]*$', tx):
        tx = hexify(tx)
    return make_request(blockr_url, '{"hex":"%s"}' % tx)


def helloblock_pushtx(tx):
    if not re.match('^[0-9a-fA-F]*$', tx):
        tx = hexify(tx)
    return make_request('https://mainnet.helloblock.io/v1/transactions',
                        'rawTxHex='+tx)

def webbtc_pushtx(tx, network='btc'):
    if network == 'testnet':
        webbtc_url = 'http://test.webbtc.com/relay_tx.json'
    elif network == 'btc':
        webbtc_url = 'http://webbtc.com/relay_tx.json'
    else:
        raise Exception(
            'Unsupported network {0} for blockr_pushtx'.format(network))

    if not re.match('^[0-9a-fA-F]*$', tx):
        tx = hexify(tx)
    return json.loads(make_request(webbtc_url, 'tx=%s' % tx))

pushtx_getters = {
    'bci': bci_pushtx,
    'blockr': blockr_pushtx,
    'webbtc': webbtc_pushtx,
    'helloblock': helloblock_pushtx
}


def pushtx(*args, **kwargs):
    svc = kwargs.get('source', '')
    f = pushtx_getters.get(svc, blockr_pushtx)
    return f(*args)


def last_block_height(network='btc'):
    if network == 'testnet':
        data = make_request('http://tbtc.blockr.io/api/v1/block/info/last')
        jsonobj = json.loads(data)
        return jsonobj["data"]["nb"]
    data = make_request('https://blockchain.info/latestblock')
    jsonobj = json.loads(data)
    return jsonobj["height"]


# Gets a specific transaction
def bci_fetchtx(txhash):
    if isinstance(txhash, list):
        return [bci_fetchtx(h) for h in txhash]
    if not re.match('^[0-9a-fA-F]*$', txhash):
        txhash = hexify(txhash)
    data = make_request('https://blockchain.info/rawtx/'+txhash+'?format=hex')
    return data


def blockr_fetchtx(txhash, network='btc'):
    if network == 'testnet':
        blockr_url = 'https://tbtc.blockr.io/api/v1/tx/raw/'
    elif network == 'btc':
        blockr_url = 'https://btc.blockr.io/api/v1/tx/raw/'
    else:
        raise Exception(
            'Unsupported network {0} for blockr_fetchtx'.format(network))
    if isinstance(txhash, list):
        txhash = ','.join([hexify(x) if not re.match('^[0-9a-fA-F]*$', x)
                           else x for x in txhash])
        jsondata = json.loads(make_request(blockr_url + txhash))
        return [d['tx']['hex'] for d in jsondata['data']]
    else:
        if not re.match('^[0-9a-fA-F]*$', txhash):
            txhash = hexify(txhash)
        jsondata = json.loads(make_request(blockr_url+txhash))
        return st(jsondata['data']['tx']['hex'])    # added st() to repair unicode return hex strings for python 2


def helloblock_fetchtx(txhash, network='btc'):
    if not re.match('^[0-9a-fA-F]*$', txhash):
        txhash = hexify(txhash)
    if network == 'testnet':
        url = 'https://testnet.helloblock.io/v1/transactions/'
    elif network == 'btc':
        url = 'https://mainnet.helloblock.io/v1/transactions/'
    else:
        raise Exception(
            'Unsupported network {0} for helloblock_fetchtx'.format(network))
    data = json.loads(make_request(url + txhash))["data"]["transaction"]
    o = {
        "locktime": data["locktime"],
        "version": data["version"],
        "ins": [],
        "outs": []
    }
    for inp in data["inputs"]:
        o["ins"].append({
            "script": inp["scriptSig"],
            "outpoint": {
                "index": inp["prevTxoutIndex"],
                "hash": inp["prevTxHash"],
            },
            "sequence": 4294967295
        })
    for outp in data["outputs"]:
        o["outs"].append({
            "value": outp["value"],
            "script": outp["scriptPubKey"]
        })
    from bitcoin.transaction import serialize
    from bitcoin.transaction import txhash as TXHASH
    tx = serialize(o)
    assert TXHASH(tx) == txhash
    return tx

def webbtc_fetchtx(txhash, network='btc'):
    if network == 'testnet':
        webbtc_url = 'http://test.webbtc.com/tx/'
    elif network == 'btc':
        webbtc_url = 'http://webbtc.com/tx/'
    else:
        raise Exception(
            'Unsupported network {0} for webbtc_fetchtx'.format(network))
    if not re.match('^[0-9a-fA-F]*$', txhash):
        txhash = hexify(txhash)
    hexdata = make_request(webbtc_url + txhash + ".hex")
    return st(hexdata)

fetchtx_getters = {
    'bci': bci_fetchtx,
    'blockr': blockr_fetchtx,
    'webbtc': webbtc_fetchtx,       #   http://test.webbtc.com/tx/txid.[hex,json, bin]
    'helloblock': helloblock_fetchtx
}


def fetchtx(*args, **kwargs):
    svc = kwargs.get("source", "")
    f = fetchtx_getters.get(svc, blockr_fetchtx)
    return f(*args)


def firstbits(address):
    if len(address) >= 25:
        return make_request('https://blockchain.info/q/getfirstbits/'+address)
    else:
        return make_request(
            'https://blockchain.info/q/resolvefirstbits/'+address)


def get_block_at_height(height):
    j = json.loads(st(make_request("https://blockchain.info/block-height/" +
                   str(height)+"?format=json")))
    for b in j['blocks']:
        if b['main_chain'] is True:
            return b
    raise Exception("Block at this height not found")


def _get_block(inp):
    if len(str(inp)) < 64:
        return get_block_at_height(inp)
    else:
        return json.loads(make_request(
                          'https://blockchain.info/rawblock/'+inp))


def bci_get_block_header_data(inp):
    j = _get_block(inp)
    return {
        'version': j['ver'],
        'hash': j['hash'],
        'prevhash': j['prev_block'],
        'timestamp': j['time'],
        'merkle_root': j['mrkl_root'],
        'bits': j['bits'],
        'nonce': j['nonce'],
    }

def blockr_get_block_header_data(height, network='btc'):
    if network == 'testnet':
        blockr_url = "http://tbtc.blockr.io/api/v1/block/raw/"
    elif network == 'btc':
        blockr_url = "http://btc.blockr.io/api/v1/block/raw/"
    else:
        raise Exception(
            'Unsupported network {0} for blockr_get_block_header_data'.format(network))

    k = json.loads(make_request(blockr_url + str(height)))
    j = k['data']
    return {
        'version': j['version'],
        'hash': j['hash'],
        'prevhash': j['previousblockhash'],
        'timestamp': j['time'],
        'merkle_root': j['merkleroot'],
        'bits': int(j['bits'], 16),
        'nonce': j['nonce'],
    }

def get_block_timestamp(height, network='btc'):
    if network == 'testnet':
        blockr_url = "http://tbtc.blockr.io/api/v1/block/info/"
    elif network == 'btc':
        blockr_url = "http://btc.blockr.io/api/v1/block/info/"
    else:
        raise Exception(
            'Unsupported network {0} for get_block_timestamp'.format(network))

    import time, calendar
    if isinstance(height, list):
        k = json.loads(make_request(blockr_url + ','.join([str(x) for x in height])))
        o = {x['nb']: calendar.timegm(time.strptime(x['time_utc'],
             "%Y-%m-%dT%H:%M:%SZ")) for x in k['data']}
        return [o[x] for x in height]
    else:
        k = json.loads(make_request(blockr_url + str(height)))
        j = k['data']['time_utc']
        return calendar.timegm(time.strptime(j, "%Y-%m-%dT%H:%M:%SZ"))

block_header_data_getters = {
    'bci': bci_get_block_header_data,
    'blockr': blockr_get_block_header_data
}

def get_block_header_data(inp, **kwargs):
    f = block_header_data_getters.get(kwargs.get('source', ''),
                                      blockr_get_block_header_data)
    return f(inp, **kwargs)

def get_txs_in_block(inp):
    j = _get_block(inp)
    hashes = [t['hash'] for t in j['tx']]
    return hashes


def get_block_height(txid, network='btc'):
    if network == 'btc':
        j = json.loads(make_request('https://blockchain.info/rawtx/%s' % txid))
        return j['block_height']
    else:
        j = json.loads(make_request('http://tbtc.blockr.io/api/v1/tx/info/%s' % txid))
        return j['data']['block']


def get_block_coinbase(txval):
    j = _get_block(txval)
    cb = bytearray.fromhex(j['tx'][0]['inputs'][0]['script'])
    alpha = set(map(chr, list(range(32, 126))))
    res = ''.join([x for x in cb.decode('utf-8') if x in alpha])
    if ord(res[0]) == len(res)-1:
        return res[1:]
    return res


def biteasy_search(*args):
    if len(args) == 2 and args[-1] in ('btc', 'testnet'):
        q, network = args
    else:
        q, network = args[0], 'btc'
    base_url = 'https://api.biteasy.com/%s/v1/search?q=' % \
               ('blockchain' if network == 'btc' else 'testnet')
    data = make_request(base_url + str(q))
    data = json.loads(data)     # we're left with {'results': [...], 'type': BLOCK}
    # TODO: parse different types, eg BLOCK
    return data.get('data', repr(data))

