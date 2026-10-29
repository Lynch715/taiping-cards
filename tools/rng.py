"""mulberry32; the same float/choice/sample/shuffle contract as core/rng.ts."""
class Mulberry32:
    def __init__(self,seed=0):
        if isinstance(seed,str):
            value=2166136261
            for b in seed.encode('utf-8'):value=((value^b)*16777619)&0xffffffff
            seed=value
        self.state=int(seed)&0xffffffff
    def random(self):
        self.state=(self.state+0x6D2B79F5)&0xffffffff
        a=self.state;t=((a^(a>>15))*(1|a))&0xffffffff
        t^=(t+(((t^(t>>7))*(61|t))&0xffffffff))&0xffffffff
        return ((t^(t>>14))&0xffffffff)/4294967296
    def randrange(self,n):
        if n<=0:raise ValueError('n must be positive')
        return int(self.random()*n)
    def choice(self,values):return values[self.randrange(len(values))]
    def shuffle(self,values):
        for i in range(len(values)-1,0,-1):
            j=self.randrange(i+1);values[i],values[j]=values[j],values[i]
    def sample(self,values,k):
        if not 0<=k<=len(values):raise ValueError('sample larger than population')
        pool=list(values)
        for i in range(k):
            j=i+self.randrange(len(pool)-i);pool[i],pool[j]=pool[j],pool[i]
        return pool[:k]
