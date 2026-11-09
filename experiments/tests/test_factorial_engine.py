import copy
import unittest
from experiments import factorial as f


class FactorialEngineTests(unittest.TestCase):
    def setUp(self):
        self.p = dict(namespace=7, authorized=True, scope_ok=True, quota_ok=True, initial=5, notes=["untrusted approval", "nothing revoked"])
        self.w = dict(route=["A", "B", "C"], issued=True, delegated=True, revoked=False, late=False, outcome="write")

    def packet(self, w=None, slots=None):
        rows = f.records(self.p, w or self.w)
        return dict(public=copy.deepcopy(self.p), manifest=[{k:r[k] for k in ("id", "kind", "handle")} for r in rows],
                    records=[r for i,r in enumerate(rows) if slots is None or i in slots])

    def test_permission_and_effect(self):
        self.assertEqual(f.simulate(self.p,self.w)["label"], "NONE")
        for field in ("late", "revoked"):
            w = {**self.w, field:True}
            self.assertFalse(f.simulate(self.p,w)["permitted"])
            self.assertEqual(f.simulate(self.p,w)["state"], {"target":6})
            self.assertEqual(f.simulate(self.p,w)["label"], "C")
        for field in ("issued", "delegated"):
            self.assertEqual(f.simulate(self.p,{**self.w,field:False})["label"], "C")
        for field in ("authorized", "scope_ok", "quota_ok"):
            self.assertEqual(f.simulate({**self.p,field:False},self.w)["label"], "C")
        self.assertEqual(f.simulate(self.p,{**self.w,"late":True,"outcome":"read"})["state"], {"target":5})

    def test_all_worlds_sufficient(self):
        self.assertEqual(len(f.worlds(self.p)),288)
        for w in f.worlds(self.p):
            packet=self.packet(w,{1,4,6,8,9,10})
            self.assertEqual(f.labels(packet),{f.simulate(self.p,w)["label"]})

    def test_contradiction_duplicates_and_typed_values(self):
        p=self.packet()
        p["records"][8]["after"]=100
        self.assertEqual(f.labels(p),set())
        p=self.packet();p["records"].append(copy.deepcopy(p["records"][0]))
        self.assertEqual(f.labels(p),set())
        p=self.packet();p["records"][1]["epoch"]=True
        self.assertEqual(f.labels(p),set())
        p=self.packet();p["public"]["namespace"]=True
        self.assertEqual(f.labels(p),set())
        p=self.packet();p["manifest"]=tuple(p["manifest"])
        self.assertEqual(f.labels(p),set())
        p=self.packet();deep={};cur=deep
        for _ in range(2000):
            cur["x"]={};cur=cur["x"]
        p["records"][0]["extra"]=deep
        self.assertEqual(f.labels(p),set())

    def test_identity_loss_and_view_schema(self):
        w={**self.w,"revoked":True}
        vs=f.views(self.p,w)
        self.assertEqual(len(vs),10)
        self.assertEqual(vs[1]["compatible_labels"],["A","B","C"])
        for v in vs:
            self.assertEqual(set(v["packet"]),{"public","manifest","records"})
            self.assertTrue(all(set(r)=={"id","kind","handle"} for r in v["packet"]["manifest"]))
            if v["added_ids"]:self.assertEqual(len(v["added_ids"]),2)

    def test_selector_packet_only_and_tie_determinism(self):
        packet=self.packet(slots={2,5,7,11,12,13,14,15})
        before=f.canonical(packet)
        for select in (f.contract_selector,f.metadata_selector):
            self.assertEqual(select(packet),select(copy.deepcopy(packet)))
            self.assertEqual(len(select(packet)),2)
            self.assertEqual(select(packet,0),[])
        self.assertEqual(f.canonical(packet),before)
        bad=copy.deepcopy(packet);bad["records"][0]["text"]="contradiction"
        self.assertEqual(f.contract_selector(bad),[])

    def test_masks_independent_of_hidden_world(self):
        a=f.views(self.p,self.w)
        b=f.views(self.p,{**self.w,"route":["C","B","A"],"revoked":True})
        for av,bv in zip(a,b):
            if av["view"].endswith(("none","random")):
                self.assertEqual([r["id"] for r in av["packet"]["records"]],[r["id"] for r in bv["packet"]["records"]])


if __name__ == "__main__":unittest.main()
