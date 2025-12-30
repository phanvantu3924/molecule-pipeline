class RankerAgent:
    def score(self, props, violations):
        return props["qed"] - 0.1 * violations

    def rank(self, molecules, top_k):
        molecules.sort(key=lambda x: x["score"], reverse=True)
        return molecules[:top_k]
