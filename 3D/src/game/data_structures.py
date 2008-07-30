class keywords(object):
    def __init__(self, keywords=[]):
        self.keywords = dict([(k,1) for k in keywords])
    def add(self, keyword):
        if self.keywords.has_key(keyword): self.keywords[keyword] += 1
        else: self.keywords[keyword] = 1
    def remove(self, keyword):
        self.keywords[keyword] -= 1
        if self.keywords[keyword] == 0: del(self.keywords[keyword])
    def clear(self):
        self.keywords.clear()
    def __contains__(self, keyword):
        return self.keywords.__contains__(keyword)
    def __iter__(self):
        return iter(self.keywords)
    def __str__(self):
        return ', '.join([k.title() for k in self.keywords.keys()])
    def __repr__(self):
        return repr(self.keywords.keys())

if __name__ == "__main__":
    import copy
    k = keywords()
    k.add("haste")
    k.add("forestwalk")
    k2 = copy.deepcopy(k)
    k2.add("first-strike")
