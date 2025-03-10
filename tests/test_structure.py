import enum
import sys
import typing

import pytest
from pytest import raises

from typedpy import Structure, DecimalNumber, PositiveInt, String, Enum, Field, Integer, Map, Array, AnyOf, NoneField, \
    DateField, DateTime
from typedpy.structures import FinalStructure, unique, MAX_NUMBER_OF_INSTANCES_TO_VERIFY_UNIQUENESS


class Venue(enum.Enum):
    NYSE = enum.auto()
    CBOT = enum.auto()
    AMEX = enum.auto()
    NASDAQ = enum.auto()


class Trader(Structure):
    lei: String(pattern='[0-9A-Z]{18}[0-9]{2}$')
    alias: String(maxLength=32)


def test_optional_fields():
    class Trade(Structure):
        notional: DecimalNumber(maximum=10000, minimum=0)
        quantity: PositiveInt(maximum=100000, multiplesOf=5)
        symbol: String(pattern='[A-Z]+$', maxLength=6)
        buyer: Trader
        seller: Trader
        venue: Enum[Venue]
        comment: String
        _optional = ["comment", "venue"]

    assert set(Trade._required) == {'notional', 'quantity', 'symbol', 'buyer', 'seller'}
    Trade(notional=1000, quantity=150, symbol="APPL",
          buyer=Trader(lei="12345678901234567890", alias="GSET"),
          seller=Trader(lei="12345678901234567888", alias="MSIM"),
          timestamp="01/30/20 05:35:35",
          )


def test_optional_fields_required_overrides():
    class Trade(Structure):
        notional: DecimalNumber(maximum=10000, minimum=0)
        quantity: PositiveInt(maximum=100000, multiplesOf=5)
        symbol: String(pattern='[A-Z]+$', maxLength=6)
        buyer: Trader
        seller: Trader
        venue: Enum[Venue]
        comment: String
        _optional = ["comment", "venue"]
        _required = []

    Trade()


@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires python3.9 or higher")
def test_field_by_name_fins_annotated_fields():
    class Trade(Structure):
        notional: DecimalNumber(maximum=10000, minimum=0)
        quantity: PositiveInt(maximum=100000, multiplesOf=5)
        symbol: String(pattern='[A-Z]+$', maxLength=6)
        buyer: Trader
        my_list: list[str]
        seller: typing.Optional[Trader]
        venue: Enum[Venue]
        comment: String
        _optional = ["comment", "venue"]
        _required = []

    field_names = Trade.get_all_fields_by_name().keys()
    for f in {"notional", "quantity", "seller", "symbol", "buyer", "my_list"}:
        assert f in field_names


def test_optional_fields_required_overrides1():
    class Trade(Structure):
        venue: Enum[Venue]
        comment: String
        _optional = ["venue"]
        _required = ["venue"]

    with raises(TypeError) as excinfo:
        Trade(comment="asdasd")
    assert "missing a required argument: 'venue'" in str(excinfo.value)


@pytest.fixture(scope="session")
def Point():
    from math import sqrt

    class PointClass:
        def __init__(self, x, y):
            self.x = x
            self.y = y

        def size(self):
            return sqrt(self.x ** 2 + self.y ** 2)

    return PointClass


def test_field_of_class(Point):
    class Foo(Structure):
        i: int
        point: Field[Point]

    foo = Foo(i=5, point=Point(3, 4))
    assert foo.point.size() == 5


@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires python3.9 or higher")
def test_ignore_none(Point):
    class Foo(Structure):
        i: list[int]
        maybe_date: typing.Optional[DateField]
        _ignore_none = True

    assert Foo(i=[5], maybe_date=None).i == [5]
    assert Foo(i=[1]).maybe_date is None
    assert Foo(i=[1], maybe_date=None).i[0] == 1
    assert Foo(i=[5], maybe_date="2020-01-31").i[0] == 5
    with raises(ValueError):
        assert Foo(i=[5], maybe_date="2020-01-31a")


def test_do_not_ignore_none(Point):
    class Foo(Structure):
        i = Integer
        point: Field[Point]
        _ignore_none = False

    with raises(TypeError) as excinfo:
        Foo(i=None, point=Point(3, 4))
    assert "i: Got None; Expected a number" in str(excinfo.value)


def test_do_not_ignore_none_for_required_fields(Point):
    class Foo(Structure):
        i: int
        date = typing.Optional[DateField]
        _ignore_none = True

    with raises(TypeError) as excinfo:
        Foo(i=None)
    assert "i: Got None; Expected a number" in str(excinfo.value)


def test_field_of_class_typeerror(Point):
    class Foo(Structure):
        i: int
        point: Field[Point]

    with raises(TypeError) as excinfo:
        Foo(i=5, point="xyz")
    assert "point: Expected <class 'test_structure.Point.<locals>.PointClass'>; Got 'xyz'" in str(
        excinfo.value)


def test_using_arbitrary_class_in_anyof(Point):
    class Foo(Structure):
        i: int
        point: AnyOf[Point, int]

    assert Foo(i=1, point=2).point == 2


def test_using_arbitrary_class_in_union(Point):
    class Foo(Structure):
        i: int
        point: typing.Union[Point, int]

    assert Foo(i=1, point=2).point == 2


def test_optional(Point):
    class Foo(Structure):
        i: int
        point: typing.Optional[Point]

    assert Foo(i=1).point is None
    assert Foo(i=1, point=None).point is None
    foo = Foo(i=1, point=Point(3, 4))
    assert foo.point.size() == 5
    foo.point = None
    assert foo.point is None
    foo.point = Point(3, 4)
    assert foo.point.size() == 5


def test_optional_err(Point):
    class Foo(Structure):
        i: int
        point: typing.Optional[Point]

    with raises(ValueError) as excinfo:
        Foo(i=1, point=3)
    assert "point: 3 Did not match any field option" in str(
        excinfo.value)


def test_field_of_class_in_map(Point):
    class Foo(Structure):
        i: int
        point_by_int: Map[Integer, Field[Point]]

    foo = Foo(i=5, point_by_int={1: Point(3, 4)})
    assert foo.point_by_int[1].size() == 5


def test_field_of_class_in_map_simpler_syntax(Point):
    class Foo(Structure):
        i: int
        point_by_int: Map[Integer, Point]

    foo = Foo(i=5, point_by_int={1: Point(3, 4)})
    assert foo.point_by_int[1].size() == 5


def test_field_of_class_in_map_typerror(Point):
    class Foo(Structure):
        i: int
        point_by_int: Map[Integer, Field[Point]]

    with raises(TypeError) as excinfo:
        Foo(i=5, point_by_int={1: Point(3, 4), 2: 3})
    assert "point_by_int_value: Expected <class 'test_structure.Point.<locals>.PointClass'>; Got 3" in str(
        excinfo.value)


def test_field_of_class_in_map__simpler_syntax_typerror(Point):
    class Foo(Structure):
        i: int
        point_by_int: Map[Integer, Point]

    with raises(TypeError) as excinfo:
        Foo(i=5, point_by_int={1: Point(3, 4), 2: 3})
    assert "point_by_int_value: Expected <class 'test_structure.Point.<locals>.PointClass'>; Got 3" in str(
        excinfo.value)


def test_simple_invalid_type():
    with raises(TypeError) as excinfo:
        class Foo(Structure):
            i = Array["x"]

    assert "Unsupported field type in definition: 'x'" in str(
        excinfo.value)


def test_simple_nonefield_usage():
    class Foo(Structure):
        a = Array[AnyOf[Integer, NoneField]]

    foo = Foo(a=[1, 2, 3, None, 4])
    assert foo.a == [1, 2, 3, None, 4]


def test_auto_none_conversion():
    class Foo(Structure):
        a = Array[AnyOf[Integer, None]]

    foo = Foo(a=[1, 2, 3, None, 4])
    assert foo.a == [1, 2, 3, None, 4]


def test_final_structure_violation():
    class Foo(FinalStructure):
        s: str

    with raises(TypeError) as excinfo:
        class Bar(Foo): pass
    assert "Tried to extend Foo, which is a FinalStructure. This is forbidden" in str(
        excinfo.value)


def test_final_structure_no_violation():
    class Foo(Structure):
        s: str

    class Bar(Foo, FinalStructure): pass


def test_unique_violation():
    @unique
    class Foo(Structure):
        s: str
        i: int

    Foo(s="xxx", i=1)
    Foo(s="xxx", i=2)
    with raises(ValueError) as excinfo:
        Foo(s="xxx", i=1)
    assert "Instance copy in Foo, which is defined as unique. Instance is" \
           " <Instance of Foo. Properties: i = 1, s = 'xxx'>" in str(
        excinfo.value)


def test_unique_violation_by_update():
    @unique
    class Foo(Structure):
        s: str
        i: int

    Foo(s="xxx", i=1)
    foo = Foo(s="xxx", i=2)
    with raises(ValueError) as excinfo:
        foo.i = 1
    assert "Instance copy in Foo, which is defined as unique. Instance is" \
           " <Instance of Foo. Properties: i = 1, s = 'xxx'>" in str(
        excinfo.value)


def test_unique_violation_stop_checking__if_too_many_instances():
    @unique
    class Foo(Structure):
        i: int

    for i in range(MAX_NUMBER_OF_INSTANCES_TO_VERIFY_UNIQUENESS):
        Foo(i=i)
    Foo(i=1)
    Foo(i=1)


def test_copy_with_overrides():
    class Trade(Structure):
        notional: DecimalNumber(maximum=10000, minimum=0)
        quantity: PositiveInt(maximum=100000, multiplesOf=5)
        symbol: String(pattern='[A-Z]+$', maxLength=6)
        timestamp = DateTime
        buyer: Trader
        seller: Trader
        venue: Enum[Venue]
        comment: String
        _optional = ["comment", "venue"]

    trade_1 = Trade(notional=1000, quantity=150, symbol="APPL",
                    buyer=Trader(lei="12345678901234567890", alias="GSET"),
                    seller=Trader(lei="12345678901234567888", alias="MSIM"),
                    timestamp="01/30/20 05:35:35",
                    )
    trade_2 = trade_1.shallow_clone_with_overrides(notional=500)
    assert trade_2.notional == 500
    trade_2.notional = 1000
    assert trade_2 == trade_1


def test_defect_required_should_propagate_with_ignore_none():
    class Foo(Structure):
        a = Integer

    class Bar(Foo):
        s = String
        _ignore_none = True

    with raises(TypeError) as excinfo:
        Bar(s="x", a=None)
    assert "a: Got None; Expected a number" in str(excinfo.value)
