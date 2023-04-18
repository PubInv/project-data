import yaml
from typing import Generator, Iterable, NamedTuple, Protocol
import urllib.request

def openFileOrUrl(path: str):
    if (path.startswith('http')):
        return urllib.request.urlopen(path)
    else:
        return open(path, "rb")

class SupplyAtom(NamedTuple):
    identifier: str
    description: str
    # link: str

    # only consider the identifier field when hashing or comparing
    def __hash__(self) -> int:
        return self.identifier.__hash__()

    def __eq__(self, __o: object) -> bool:
        return self.identifier == __o.identifier

    @staticmethod
    def parse(yml):
        identifier = yml.get("identifier")
        if (identifier == None):
            raise ValueError("missing SupplyAtom identifier")
        description = yml.get("description")
        # link = yml.get("link")
        return SupplyAtom(identifier, description) #, link)

    @staticmethod
    def parseArray(yml):
        atoms = []
        if (yml == None): return atoms
        for i in range(len(yml)):
            atom = SupplyAtom.parse(yml[i])
            atoms.append(atom)
        return atoms

class MakerSupplier(NamedTuple):
    name: str
    supplies: frozenset[SupplyAtom]
    tools: frozenset[SupplyAtom]

    @staticmethod
    def create(name: str, supplies: Iterable[SupplyAtom], tools: Iterable[SupplyAtom]):
        return MakerSupplier(name, frozenset(supplies), frozenset(tools))

class Supplier(NamedTuple):
    name: str
    supplies: frozenset[SupplyAtom]

    @staticmethod
    def create(name: str, supplies: Iterable[SupplyAtom]):
        return Supplier(name, frozenset(supplies))


class Maker(NamedTuple):
    name: str
    tools: frozenset[SupplyAtom]

    @staticmethod
    def create(name: str, tools: Iterable[SupplyAtom]):
        return Maker(name, frozenset(tools))

    def compatible(self, tools: Iterable[SupplyAtom]):
        for tool in tools:
            if tool not in self.tools:
                return False
        return True


def slurpOKW(path: str):
    with openFileOrUrl(path) as file_stream:
        yml = yaml.safe_load(file_stream)
        name = yml.get("title")
        supplies = SupplyAtom.parseArray(yml.get("supply-atoms"))
        tools = SupplyAtom.parseArray(yml.get("tool-list-atoms"))
        toolCount = len(tools)
        if (len(supplies) == 0):
            if (toolCount == 0): raise ValueError("Invalid OKW")
            return Maker.create(name, tools)
        else:
            return Supplier.create(name, supplies) if (toolCount == 0) else MakerSupplier.create(name, supplies, tools)

class ProductDesign(NamedTuple):
    name: str
    product: SupplyAtom
    bom: frozenset[SupplyAtom]
    tools: frozenset[SupplyAtom]
    bomOutputs: frozenset[SupplyAtom]

    @staticmethod
    def create(name: str, product: SupplyAtom, bom: Iterable[SupplyAtom], tools: Iterable[SupplyAtom], bomOutput: Iterable[SupplyAtom]):
        return ProductDesign(name, product, frozenset(bom), frozenset(tools), frozenset(bomOutput))
        

    @staticmethod
    def slurp(path: str):
        with openFileOrUrl(path) as file_stream:
            yml = yaml.safe_load(file_stream)
            name = yml.get("title")
            product = SupplyAtom.parse(yml.get("product-atom"))
            bom = SupplyAtom.parseArray(yml.get("bom-atoms"))
            tools = SupplyAtom.parseArray(yml.get("tool-list-atoms"))
            bomOutput = [] #SupplyAtom.parseArray(yml.get("bom-output-atoms"))
            return ProductDesign(name, product, bom, tools, bomOutput)

class SupplyTree(Protocol):
    def getProduct() -> SupplyAtom:
        ...

    def print(indent: int):
        ...


class SupplierSupplyTree(NamedTuple):
    product: SupplyAtom
    supplier: Supplier

    def getProduct(self):
        return self.product

    def print(self, indent: int):
        buffer = ' ' * indent
        print(buffer + "Supplier: {}/{}".format(self.supplier.name,
              self.product.description))


class MakerSupplyTree(NamedTuple):
    product: SupplyAtom
    design: ProductDesign
    maker: Maker
    supplies: frozenset[SupplyTree]

    def getProduct(self):
        return self.product

    def print(self, indent: int):
        buffer = ' ' * indent
        print(buffer + "Maker: {}/{}".format(self.maker.name, self.design.name))
        for s in self.supplies:
            s.print(indent + 4)


class MissingSupplyTree(NamedTuple):
    product: SupplyAtom

    def getProduct(self):
        return self.product

    def print(self, indent: int):
        buffer = ' ' * indent
        print(buffer + "Missing:  {}".format(self.product.description))


class SupplyProblemSpace(NamedTuple):
    suppliers: frozenset[Supplier]
    makers: frozenset[Maker]
    designs: frozenset[ProductDesign]

    @staticmethod
    def create(suppliers: Iterable[Supplier], makers: Iterable[Maker], designs: Iterable[ProductDesign]):
        return SupplyProblemSpace(frozenset(suppliers), frozenset(makers), frozenset(designs))

    def query(self, product: SupplyAtom) -> Generator[SupplyTree, None, None]:
        found = False
        for supplier in self.suppliers:
            for supply in supplier.supplies:
                if supply == product:
                    found = True
                    yield SupplierSupplyTree(product, supplier)
        for design in self.designs:
            if design.product == product:
                trees = []
                for bom in design.bom:
                    for tree in self.query(bom):
                        trees.append(tree)
                for maker in self.makers:
                    if maker.compatible(design.tools):
                        found = True
                        yield MakerSupplyTree(product, design, maker, frozenset(trees))
        if found == False:
            yield MissingSupplyTree(product)


#Slurp Sample
helpfulChair = ProductDesign.slurp("https://raw.githubusercontent.com/helpfulengineering/library/main/alpha/okh/okh-chair-helpful.yml")
devhawkMaker = slurpOKW("https://raw.githubusercontent.com/helpfulengineering/library/main/alpha/okw/DevhawkEngineering.okw.yml")
chairPartSupplier = slurpOKW("https://raw.githubusercontent.com/helpfulengineering/library/main/alpha/okw/ChairParts.okw.yml")

# Mask Sample

# Product atoms
fabricMask = SupplyAtom("QH00001", "Fabric Mask")

# BOM atoms
nwpp = SupplyAtom("QH00002", "Non-woven Polypropylene bag")
biasTape = SupplyAtom("Q4902580", "Bias tape")
tinTie = SupplyAtom("QH00003", "Coffee tin tie")
pipeCleaner = SupplyAtom("Q3355092", "pipe cleaners")

# Tool Atoms
sewingMachine = SupplyAtom("Q49013", "Sewing machine")
scissors = SupplyAtom("Q40847", "Scissors")
pins = SupplyAtom("Q111591519", "Pins")
measuringTape = SupplyAtom("Q107196205", "Measuring Tape")

# BOM Output Atoms
scrapFabric = SupplyAtom("Q1378670", "Scrap Fabric")

# Chair sample

# Product atoms
chair = SupplyAtom("Q15026", "chair")
chairLeg = SupplyAtom("QH100", "chair leg")
chairSeat = SupplyAtom("QH101", "chair seat")
chairBack = SupplyAtom("QH102", "chair back")

# BOM atoms
fabric = SupplyAtom("QH103", "fabric")
wood = SupplyAtom("QH104", "wood")
stuffing = SupplyAtom("QH105", "stuffing")
upholstery = SupplyAtom("QH106", "upholstery")
frame = SupplyAtom("QH107", "frame")
nails = SupplyAtom("QH108", "nails")

# Tool Atoms
plane = SupplyAtom("Q204260", "plane")
lathe = SupplyAtom("Q187833", "lathe")
hammer = SupplyAtom("Q25294", "hammer")
saw = SupplyAtom("Q125356", "saw")

# designs

chairDesign = ProductDesign.create(
    "Funky Chair Design",
    chair,
    [chairLeg, chairSeat, chairBack, nails],
    [hammer],
    [])

legDesign = ProductDesign.create(
    "Leg Design",
    chairLeg,
    [wood],
    [lathe],
    [])

seatDesign1 = ProductDesign.create(
    "Seat Design 1",
    chairSeat,
    [fabric],
    [plane],
    [])

seatDesign2 = ProductDesign.create(
    "Seat Design 2",
    chairSeat,
    [frame, stuffing, upholstery],
    [sewingMachine],
    [])

supplierRaw = Supplier.create("raw supplies",
                              [nwpp, biasTape, tinTie, pipeCleaner, fabric, wood, upholstery, frame, nails])

supplierRobert = Supplier.create("Robert's Chair Parts", [chairBack, chairLeg])

makerJames = Maker.create("James Maker Space", [
                          sewingMachine, scissors, pins, measuringTape])
makerHarry = Maker.create("Devhawk Engineering", [hammer, lathe, plane])

maskDesign = ProductDesign.create(
    "Surge Mask",
    fabricMask,
    [nwpp, biasTape, tinTie, pipeCleaner],
    [sewingMachine, scissors, pins, scissors],
    [scrapFabric])

problemSpace = SupplyProblemSpace.create(
    [supplierRaw, supplierRobert], [makerJames, makerHarry], [maskDesign, chairDesign, seatDesign1, seatDesign2, legDesign])

for t in problemSpace.query(chair):
    t.print(0)



