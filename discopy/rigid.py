# -*- coding: utf-8 -*-

"""
The free rigid category, i.e. diagrams with cups and caps.

Summary
-------

.. autosummary::
    :template: class.rst
    :nosignatures:
    :toctree:

    Ob
    Ty
    Layer
    Diagram
    Box
    Cup
    Cap
    Category
    Functor

Axioms
------

>>> unit, s, n = Ty(), Ty('s'), Ty('n')
>>> t = n.r @ s @ n.l
>>> assert t @ unit == t == unit @ t
>>> assert t.l.r == t == t.r.l
>>> left_snake, right_snake = Id(n.r).transpose(left=True), Id(n.l).transpose()
>>> assert left_snake.normal_form() == Id(n) == right_snake.normal_form()
>>> from discopy import drawing
>>> drawing.equation(
...     left_snake, Id(n), right_snake, figsize=(4, 2),
...     path='docs/_static/imgs/rigid/snake-equation.png')

.. image:: ../_static/imgs/rigid/snake-equation.png
    :align: center
"""

from __future__ import annotations

from discopy import cat, monoidal, symmetric, messages, rewriting
from discopy.cat import AxiomError, factory
from discopy.monoidal import Encoding
from discopy.utils import BinaryBoxConstructor, assert_isinstance, factory_name


class Ob(cat.Ob):
    """
    A rigid object has adjoints :meth:`Ob.l` and :meth:`Ob.r`.

    Parameters:
        name : The name of the object.
        z : The winding number.

    Example
    -------
    >>> a = Ob('a')
    >>> assert a.l.r == a.r.l == a and a != a.l.l != a.r.r
    """
    def __init__(self, name: str, z: int = 0):
        assert_isinstance(z, int)
        self._z = z
        super().__init__(name)

    @property
    def z(self) -> int:
        """
        The winding number of the object: :code:`z == 0` for generators,
        :code:`z < 0` for left adjoints and :code:`z > 0` for right adjoints.
        """
        return self._z

    @property
    def l(self) -> Ob:
        """ The left adjoint of the object. """
        return Ob(self.name, self.z - 1)

    @property
    def r(self) -> Ob:
        """ The right adjoint of the object. """
        return Ob(self.name, self.z + 1)

    def __eq__(self, other):
        if not isinstance(other, Ob):
            if isinstance(other, cat.Ob):
                return self.z == 0 and self.name == other.name
            return False
        return (self.name, self.z) == (other.name, other.z)

    def __hash__(self):
        return hash(self.name if not self.z else (self.name, self.z))

    def __repr__(self):
        return "{}({}{})".format(
            factory_name(type(self)), repr(self.name),
            ", z=" + repr(self.z) if self.z else "")

    def __str__(self):
        return str(self.name) + (
            - self.z * '.l' if self.z < 0 else self.z * '.r')

    def to_tree(self):
        tree = super().to_tree()
        if self.z:
            tree['z'] = self.z
        return tree

    @classmethod
    def from_tree(cls, tree):
        name, z = tree['name'], tree.get('z', 0)
        return cls(name=name, z=z)


@factory
class Ty(monoidal.Ty):
    """
    A rigid type is a monoidal type with rigid objects inside.

    Parameters:
        inside (tuple[Ob, ...]) : The objects inside the type.

    Example
    -------
    >>> s, n = Ty('s'), Ty('n')
    >>> assert n.l.r == n == n.r.l
    >>> assert (s @ n).l == n.l @ s.l and (s @ n).r == n.r @ s.r
    """
    ob_factory = Ob

    @property
    def l(self) -> Ty:
        """ The left adjoint of the type. """
        return Ty(*[x.l for x in self.inside[::-1]])

    @property
    def r(self) -> Ty:
        """ The right adjoint of the type. """
        return Ty(*[x.r for x in self.inside[::-1]])

    @property
    def z(self) -> int:
        """ The winding number is only defined for types of length 1. """
        if len(self) != 1:
            raise TypeError(messages.no_winding_number_for_complex_types())
        return self.inside[0].z

    def __repr__(self):
        return factory_name(type(self)) + "({})".format(', '.join(
            repr(x if x.z else x.name) for x in self.inside))

    def __lshift__(self, other):
        return self @ other.l

    def __rshift__(self, other):
        return self.r @ other


class PRO(monoidal.PRO, Ty):
    """ Objects of the free rigid monoidal category generated by 1. """
    @staticmethod
    def factory(old):
        return PRO(len(old))

    @property
    def l(self):
        """
        >>> assert PRO(2).l == PRO(2)
        """
        return self

    @property
    def r(self):
        return self


class Layer(monoidal.Layer):
    """
    A rigid layer is a monoidal layer that can be transposed.

    Parameters:
        left (Ty) : The type on the left of the layer.
        box (Box) : The box in the middle of the layer.
        right (Ty) : The type on the right of the layer.
    """
    @property
    def l(self) -> Layer:
        """ The left-transpose of the layer. """
        return type(self)(self.right.l, self.box.l, self.left.l)

    @property
    def r(self) -> Layer:
        """ The right-transpose of the layer. """
        return type(self)(self.right.r, self.box.r, self.left.r)


@factory
class Diagram(monoidal.Diagram):
    """
    A rigid diagram is a monoidal diagram
    with :class:`Cup` and :class:`Cap` boxes.

    Parameters:
        inside (tuple[Layer, ...]) : The layers of the diagram.
        dom (Ty) : The domain of the diagram, i.e. its input.
        cod (Ty) : The codomain of the diagram, i.e. its output.


    Example
    -------
    >>> I, n, s = Ty(), Ty('n'), Ty('s')
    >>> Alice, jokes = Box('Alice', I, n), Box('jokes', I, n.r @ s)
    >>> d = Alice >> Id(n) @ jokes >> Cup(n, n.r) @ Id(s)
    >>> d.draw(figsize=(3, 2),
    ...        path='docs/_static/imgs/rigid/diagram-example.png')

    .. image:: ../_static/imgs/rigid/diagram-example.png
        :align: center
    """
    over = staticmethod(lambda base, exponent: base << exponent)
    under = staticmethod(lambda base, exponent: exponent >> base)

    @classmethod
    def eval(cls, base: Ty, exponent: Ty, left=True) -> Diagram:
        return base @ cls.cups(exponent.l, exponent) if left\
            else cls.cups(exponent, exponent.r) @ base

    @classmethod
    def cups(cls, left: Ty, right: Ty) -> Diagram:
        """
        Constructs nested cups witnessing adjointness of x and y.

        >>> a, b = Ty('a'), Ty('b')
        >>> assert Diagram.cups(a, a.r) == Cup(a, a.r)
        >>> assert Diagram.cups(a @ b, (a @ b).r) ==\\
        ...     Id(a) @ Cup(b, b.r) @ Id(a.r) >> Cup(a, a.r)

        >>> Diagram.cups(a @ b, (a @ b).r).draw(figsize=(3, 1),\\
        ... margins=(0.3, 0.05), path='docs/_static/imgs/rigid/cups.png')

        .. image:: ../_static/imgs/rigid/cups.png
            :align: center
        """
        return nesting(cls.cup_factory)(left, right)

    @classmethod
    def caps(cls, left, right):
        """ Constructs nested cups witnessing adjointness of x and y.

        >>> a, b = Ty('a'), Ty('b')
        >>> assert Diagram.caps(a, a.l) == Cap(a, a.l)
        >>> assert Diagram.caps(a @ b, (a @ b).l) == (Cap(a, a.l)
        ...                 >> Id(a) @ Cap(b, b.l) @ Id(a.l))
        """
        return nesting(cls.cap_factory)(left, right)

    @staticmethod
    def fa(left, right):
        """ Forward application. """
        return Id(left) @ Diagram.cups(right.l, right)

    @staticmethod
    def ba(left, right):
        """ Backward application. """
        return Diagram.cups(left, left.r) @ Id(right)

    @staticmethod
    def fc(left, middle, right):
        """ Forward composition. """
        return Id(left) @ Diagram.cups(middle.l, middle) @ Id(right.l)

    @staticmethod
    def bc(left, middle, right):
        """ Backward composition. """
        return Id(left.r) @ Diagram.cups(middle, middle.r) @ Id(right)

    @staticmethod
    def fx(left, middle, right):
        """ Forward crossed composition. """
        return Id(left) @ Diagram.swap(middle.l, right.r) @ Id(middle) >>\
            Diagram.swap(left, right.r) @ Diagram.cups(middle.l, middle)

    @staticmethod
    def bx(left, middle, right):
        """ Backward crossed composition. """
        return Id(middle) @ Diagram.swap(left.l, middle.r) @ Id(right) >>\
            Diagram.cups(middle, middle.r) @ Diagram.swap(left.l, right)

    def curry(self, n=1, left=True) -> Diagram:
        """ Diagram currying. """
        if left:
            base, exponent = self.dom[:n], self.dom[n:]
            return base @ self.caps(exponent, exponent.l) >> self @ exponent.l
        offset = len(self.dom) - n
        base, exponent = self.dom[offset:], self.dom[:offset]
        return self.caps(exponent.r, exponent) @ base >> exponent.r @ self

    def _conjugate(self, use_left):
        inside = tuple(
            layer.l if use_left else layer.r
            for x in self.inside for layer in [Layer(*x)])
        dom = self.dom.l if use_left else self.dom.r
        cod = self.cod.l if use_left else self.cod.r
        return self.factory(inside, dom, cod)

    @property
    def l(self):
        return self._conjugate(use_left=True)

    @property
    def r(self):
        return self._conjugate(use_left=False)

    def transpose_box(self, i, left=False):
        bend_left = left
        layers = self.inside
        if bend_left:
            box_T = layers[i].box.r.dagger().transpose(left=True)
        else:
            box_T = layers[i].box.l.dagger().transpose(left=False)
        left, _, right = layers[i]
        layers_T = (Id(left) @ box_T @ Id(right)).inside.boxes
        list_of_layers = layers.boxes[:i] + layers_T + layers.boxes[i + 1:]
        layers = type(layers)(layers.dom, layers.cod, list_of_layers)
        boxes_and_offsets = tuple(zip(*(
            (box, len(left)) for left, box, _ in layers))) or ([], [])
        return self.decode(Encoding(dom, boxes_and_offsets))

    def transpose(self, left=False):
        """
        >>> a, b = Ty('a'), Ty('b')
        >>> double_snake = Id(a @ b).transpose()
        >>> two_snakes = Id(b).transpose() @ Id(a).transpose()
        >>> double_snake == two_snakes
        False
        >>> *_, two_snakes_nf = monoidal.Diagram.normalize(two_snakes)
        >>> assert double_snake == two_snakes_nf
        >>> f = Box('f', a, b)

        >>> a, b = Ty('a'), Ty('b')
        >>> double_snake = Id(a @ b).transpose(left=True)
        >>> snakes = Id(b).transpose(left=True) @ Id(a).transpose(left=True)
        >>> double_snake == two_snakes
        False
        >>> *_, two_snakes_nf = monoidal.Diagram.normalize(
        ...     snakes, left=True)
        >>> assert double_snake == two_snakes_nf
        >>> f = Box('f', a, b)
        """
        if left:
            return self.id(self.cod.l) @ self.caps(self.dom, self.dom.l)\
                >> self.id(self.cod.l) @ self @ self.id(self.dom.l)\
                >> self.cups(self.cod.l, self.cod) @ self.id(self.dom.l)
        return self.caps(self.dom.r, self.dom) @ self.id(self.cod.r)\
            >> self.id(self.dom.r) @ self @ self.id(self.cod.r)\
            >> self.id(self.dom.r) @ self.cups(self.cod, self.cod.r)

    def normal_form(self, normalizer=None, **params):
        """
        Implements the normalisation of rigid monoidal categories,
        see arxiv:1601.05372, definition 2.12.
        """
        return super().normal_form(
            normalizer=normalizer or Diagram.normalize, **params)

    normalize = rewriting.snake_removal

    def cup(self, x, y):
        if min(x, y) < 0 or max(x, y) >= len(self.cod):
            raise ValueError(f'Indices {x, y} are out of range.')
        x, y = min(x, y), max(x, y)
        for i in range(x, y - 1):
            t0, t1 = self.cod[i:i + 1], self.cod[i + 1:i + 2]
            self >>= Id(self.cod[:i]) @ Swap(t0, t1) @ Id(self.cod[i + 2:])
        t0, t1 = self.cod[y - 1:y], self.cod[y:y + 1]
        self >>= Id(self.cod[:y - 1]) @ Cup(t0, t1) @ Id(self.cod[y + 1:])
        return self


class Id(Diagram):
    """ Define an identity arrow in a free rigid category

    >>> t = Ty('a', 'b', 'c')
    >>> assert Id(t) == Diagram((), t, t)
    """
    def __init__(self, dom=Ty()):
        monoidal.Id.__init__(self, dom)
        Diagram.__init__(self, (), dom, dom)

    @property
    def l(self):
        return type(self)(self.dom.l)

    @property
    def r(self):
        return type(self)(self.dom.r)


class Box(monoidal.Box, Diagram):
    """
    A rigid box is a monoidal box in a rigid diagram.

    Parameters:
        name : The name of the box.
        dom : The domain of the box, i.e. its input.
        cod : The codomain of the box, i.e. its output.

    Example
    -------
    >>> a, b = Ty('a'), Ty('b')
    >>> Box('f', a, b.l @ b)
    rigid.Box('f', rigid.Ty('a'), rigid.Ty(rigid.Ob('b', z=-1), 'b'))
    """
    def __init__(self, name: str, dom: Ty, cod: Ty, **params):
        self._z = params.get("_z", 0)
        monoidal.Box.__init__(self, name, dom, cod, **params)
        Diagram.__init__(self, self.inside, dom, cod)

    def __eq__(self, other):
        if isinstance(other, Box):
            return self._z == other._z and cat.Box.__eq__(self, other)
        if isinstance(other, Diagram):
            return len(other) == 1 and other.boxes[0] == self\
                and (other.dom, other.cod) == (self.dom, self.cod)
        return False

    def __hash__(self):
        return hash(repr(self))

    @property
    def z(self):
        return self._z

    @property
    def l(self):
        return type(self)(
            name=self.name, dom=self.dom.l, cod=self.cod.l,
            data=self.data, _z=self._z - 1)

    @property
    def r(self):
        return type(self)(
            name=self.name, dom=self.dom.r, cod=self.cod.r,
            data=self.data, _z=self._z + 1)

    def dagger(self):
        raise AxiomError(
            "Rigid categories have no dagger, use pivotal instead.")


class Sum(monoidal.Sum, Box):
    """ A rigid sum is a monoidal sum that can be transposed. """
    @property
    def l(self) -> Sum:
        """ The left transpose of a sum, i.e. the sum of left transposes. """
        return self.sum(
            tuple(term.l for term in self.terms), self.dom.l, self.cod.l)

    @property
    def r(self) -> Sum:
        """ The right transpose of a sum, i.e. the sum of right transposes. """
        return self.sum(
            tuple(term.r for term in self.terms), self.dom.r, self.cod.r)


class Cup(BinaryBoxConstructor, Box):
    """
    The counit of the adjunction for an atomic type.

    Parameters:
        left : The atomic type.
        right : Its right adjoint.

    Example
    -------
    >>> n = Ty('n')
    >>> Cup(n, n.r)
    Cup(rigid.Ty('n'), rigid.Ty(rigid.Ob('n', z=1)))

    >>> Cup(n, n.r).draw(figsize=(2,1), margins=(0.5, 0.05),\\
    ... path='docs/_static/imgs/rigid/cup.png')

    .. image:: ../_static/imgs/rigid/cup.png
        :align: center
    """
    def __init__(self, left: Ty, right: Ty):
        if not isinstance(left, Ty):
            raise TypeError(messages.type_err(Ty, left))
        if not isinstance(right, Ty):
            raise TypeError(messages.type_err(Ty, right))
        if len(left) != 1 or len(right) != 1:
            raise ValueError(messages.cup_vs_cups(left, right))
        if left.r != right and left != right.r:
            raise AxiomError(messages.are_not_adjoints(left, right))
        BinaryBoxConstructor.__init__(self, left, right)
        Box.__init__(
            self, "Cup({}, {})".format(left, right), left @ right, Ty())
        self.draw_as_wires = True

    @property
    def l(self):
        return Cup(self.right.l, self.left.l)

    @property
    def r(self):
        return Cup(self.right.r, self.left.r)

    def dagger(self):
        """
        The dagger of a rigid cup is ill-defined.

        See also
        --------
        Use a :class:`pivotal.Cup` instead.
        """
        raise AxiomError("Rigid cups have no dagger, use pivotal instead.")

    def __repr__(self):
        return "Cup({}, {})".format(repr(self.left), repr(self.right))


class Cap(BinaryBoxConstructor, Box):
    """
    The unit of the adjunction for an atomic type.

    Parameters:
        left : The atomic type.
        right : Its left adjoint.

    Example
    -------
    >>> n = Ty('n')
    >>> Cap(n, n.l)
    Cap(rigid.Ty('n'), rigid.Ty(rigid.Ob('n', z=-1)))

    >>> Cap(n, n.l).draw(figsize=(2,1), margins=(0.5, 0.05),\\
    ... path='docs/_static/imgs/rigid/cap.png')

    .. image:: ../_static/imgs/rigid/cap.png
        :align: center
    """
    def __init__(self, left, right):
        if not isinstance(left, Ty):
            raise TypeError(messages.type_err(Ty, left))
        if not isinstance(right, Ty):
            raise TypeError(messages.type_err(Ty, right))
        if len(left) != 1 or len(right) != 1:
            raise ValueError(messages.cap_vs_caps(left, right))
        if left != right.r and left.r != right:
            raise AxiomError(messages.are_not_adjoints(left, right))
        BinaryBoxConstructor.__init__(self, left, right)
        Box.__init__(
            self, "Cap({}, {})".format(left, right), Ty(), left @ right)
        self.draw_as_wires = True

    @property
    def l(self):
        return Cap(self.right.l, self.left.l)

    @property
    def r(self):
        return Cap(self.right.r, self.left.r)

    def dagger(self):
        """
        The dagger of a rigid cap is ill-defined.

        See also
        --------
        Use a :class:`pivotal.Cap` instead.
        """
        raise AxiomError("Rigid caps have no dagger, use pivotal instead.")

    def __repr__(self):
        return "Cap({}, {})".format(repr(self.left), repr(self.right))


class Category(monoidal.Category):
    """
    A rigid category is a monoidal category
    with methods :code:`l`, :code:`r`, :code:`cups` and :code:`caps`.

    Parameters:
        ob : The type of objects.
        ar : The type of arrows.
    """
    ob, ar = Ty, Diagram


class Functor(monoidal.Functor):
    """
    A rigid functor is a monoidal functor that preserves cups and caps.

    Parameters:
        ob (Mapping[Ty, Ty]) : Map from atomic :class:`Ty` to :code:`cod.ob`.
        ar (Mapping[Box, Diagram]) : Map from :class:`Box` to :code:`cod.ar`.
        cod (Category) : The codomain of the functor.

    Example
    -------
    >>> s, n = Ty('s'), Ty('n')
    >>> Alice, Bob = Box("Alice", Ty(), n), Box("Bob", Ty(), n)
    >>> loves = Box('loves', Ty(), n.r @ s @ n.l)
    >>> love_box = Box('loves', n @ n, s)
    >>> ob = {s: s, n: n}
    >>> ar = {Alice: Alice, Bob: Bob}
    >>> ar.update({loves: Cap(n.r, n) @ Cap(n, n.l)
    ...                   >> Id(n.r) @ love_box @ Id(n.l)})
    >>> F = Functor(ob, ar)
    >>> sentence = Alice @ loves @ Bob >> Cup(n, n.r) @ Id(s) @ Cup(n.l, n)
    >>> assert F(sentence).normal_form() == Alice >> Id(n) @ Bob >> love_box
    >>> from discopy import drawing
    >>> drawing.equation(
    ...     sentence, F(sentence), symbol='$\\\\mapsto$', figsize=(5, 2),
    ...     path='docs/_static/imgs/rigid/functor-example.png')

    .. image:: ../_static/imgs/rigid/functor-example.png
        :align: center
    """
    dom = cod = Category(Ty, Diagram)

    def __call__(self, other):
        if isinstance(other, Ty) or isinstance(other, Ob) and other.z == 0:
            return super().__call__(other)
        if isinstance(other, Ob):
            if not hasattr(self.cod.ob, 'l' if other.z < 0 else 'r'):
                return self(Ob(other.name, z=0))[::-1]
            return self(other.r).l if other.z < 0 else self(other.l).r
        if isinstance(other, Cup):
            return self.cod.ar.cups(self(other.dom[:1]), self(other.dom[1:]))
        if isinstance(other, Cap):
            return self.cod.ar.caps(self(other.cod[:1]), self(other.cod[1:]))
        if isinstance(other, Box):
            if not hasattr(other, "z") or not other.z:
                return super().__call__(other)
            z = other.z
            for _ in range(abs(z)):
                other = other.l if z > 0 else other.r
            result = super().__call__(other)
            for _ in range(abs(z)):
                result = result.l if z < 0 else result.r
            return result
        return super().__call__(other)


Diagram.sum = Sum
Diagram.cup_factory, Diagram.cap_factory = Cup, Cap


def nesting(factory):
    """
    Take a :code:`factory` for cups or caps of atomic types
    and extends it recursively.

    Parameters:
        factory :
            The factory for cups or caps of atomic types, i.e. of length 1.
    """
    def method(x: Ty, y: Ty) -> Diagram:
        if len(x) == 0: return factory.id(x[:0])
        if len(x) == 1: return factory(x, y)
        head = factory(x[0], y[-1])
        if head.dom:  # We are nesting cups.
            return x[0] @ method(x[1:], y[:-1]) @ y[-1] >> head
        return head >> x[0] @ method(x[1:], y[:-1]) @ y[-1]

    return method
