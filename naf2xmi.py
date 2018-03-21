import warnings
import xml.etree.ElementTree as ET

class Namespaces(object):
    def register(self, alias, ns):
        ET.register_namespace(alias, ns)
        self.xmlns[alias] = ns
    def get(self, alias):
        return self.xmlns[alias]
    def __init__(self):
        self.xmlns = dict()
        self.register('cas', "http:///uima/cas.ecore")
        self.register('xmi', "http://www.omg.org/XMI")
        self.register('tcas', "http:///uima/tcas.ecore")
        self.register('ixatypes', "http:///ixa/ehu.eus/ixa-pipes/types.ecore")

class Parse_state(object):
    def __init__(self, raw):
        self.sofaId = "1"
        self.raw = raw
        self.omaps = { 'w' : dict(), # tokens
                       't' : dict()  # terms
        }
        self.ns = Namespaces()
        self.id = 1

    def next_id(self):
        res = str(self.id)
        self.id += 1
        return res

    def qname(self, ns, name):
        return ET.QName(self.ns.get(ns), name)

    def set_offset(self, id, b, e):
        dmap = self.omaps[id[0]]
        if dmap is None:
            raise Exception("[E] Can not guess map type using id {}".format(id))
        dmap[id] = [str(b), str(e)]

    def oRange(self, tgtids):
        if len(tgtids) == 0:
            return (0, 0)
        # guess map type according to first character in tgtid
        dmap = self.omaps[tgtids[0][0]]
        if dmap is None:
            raise Exception("[E] Can not guess map type using id {}".format(tgtids[0]))
        if tgtids[0] not in dmap:
            raise Exception("[E] undefined id {}".format(tgtids[0]))
        b, e = dmap[tgtids[0]]
        for i in range(len(tgtids) - 1):
            if tgtids[i] not in dmap:
                raise Exception("[E] undefined id {}".format(tgtids[i]))
            bb, ee = dmap[tgtids[i + 1]]
            b = min(int(b), int(bb))
            e = max(int(e), int(ee))
        return (b, e)

def parse_naf_fh():
    # TODO parse from fs
    tree = ET.parse('obama.xml')
    return tree.getroot()

def targets(elem):
    targets = []
    head = None
    if elem is None:
        return (targets, head)
    span = elem.find("span")
    if span is None:
        return (targets, head)
    for t in span.findall("target"):
        tid = t.get("id")
        if "head" in t:
            head = tid
        targets.append(tid)
    return (targets, head)

def raw(tree):
    relem = tree.find("raw")
    return relem.text

def tok(tree, pstate, out):
    text = tree.find("text")
    for wf in text.findall("wf"):
        b = int(wf.get("offset"))
        e = b + int(wf.get("length"))
        pstate.set_offset(wf.get("id"), b, e)
        tcas = ET.SubElement(out, pstate.qname('ixatypes', 'tok'))
        tcas.set(pstate.qname('xmi', 'id'), pstate.next_id())
        tcas.set('sofa', pstate.sofaId)
        tcas.set('begin', str(b))
        tcas.set('end', str(e))
        ET.tostring(tcas)

def pos(tree, pstate, out):
    terms = tree.find("terms")
    for term in terms.findall("term"):
        lemma = term.get("lemma")
        pos = term.get("pos")
        morphofeat = term.get("morphofeat")
        wids, _ = targets(term)
        b, e = pstate.oRange(wids)
        pstate.set_offset(term.get("id"), b, e)
        tcas = ET.SubElement(out, pstate.qname('ixatypes', 'lexUnit'))
        tcas.set(pstate.qname('xmi', 'id'), pstate.next_id())
        tcas.set('sofa', pstate.sofaId)
        tcas.set('begin', b)
        tcas.set('end', e)
        tcas.set('lemma', lemma)
        tcas.set('pos', pos)
        tcas.set('morphofeat', morphofeat)
        ET.tostring(tcas)

def ner(tree, pstate, out):
    entities = tree.find("entities")
    for entity in entities.findall("entity"):
        etype = entity.get("type")
        tcas = ET.SubElement(out, pstate.qname('ixatypes', 'entity'))
        tids, _ = targets(entity.find("references"))
        b, e = pstate.oRange(tids)
        tcas.set(pstate.qname('xmi', 'id'), pstate.next_id())
        tcas.set('sofa', pstate.sofaId)
        tcas.set('begin', str(b))
        tcas.set('end', str(e))
        tcas.set('type', etype)

def doc(tree, pstate, out):
    e = str(len(pstate.raw))
    topics = tree.find("topics")
    for topic in topics.findall("topic"):
        tcas = ET.SubElement(out, pstate.qname('ixatypes', 'topic'))
        tcas.set(pstate.qname('xmi', 'id'), pstate.next_id())
        tcas.set('sofa', pstate.sofaId)
        tcas.set('begin', "0")
        tcas.set('end', str(e))
        conf = topic.get("confidence")
        if conf is not None:
            conf = "1.0"
        value = topic.text
        tcas.set('confidence', conf)
        tcas.set('value', value)


def sofa(pstate, out):
    sofa = ET.SubElement(out, pstate.qname('cas', 'Sofa'))
    sofa.set(pstate.qname('xmi', 'id'), pstate.sofaId)
    sofa.set('sofaNum', "1")
    sofa.set('sofaId', "_initialView")
    sofa.set('mimeType', "text")
    sofa.set('sofaString', pstate.raw)

def main():
    try:
        naf = parse_naf_fh()
        r = raw(naf)
        pstate = Parse_state(r)
        out = ET.Element(pstate.qname('xmi', 'XMI'))
        tok(naf, pstate, out)
        pos(naf, pstate, out)
        ner(naf, pstate, out)
        doc(naf, pstate, out)
        # add sofa
        sofa(pstate, out)
        otree = ET.ElementTree(out)
        otree.write('kk.xml', encoding = "utf-8")
    except Exception as e:
        msg = "Warning: an exception occured: {}".format(e)
        warnings.warn(msg)
        raise

main()
