from decimal import Decimal


class Specification:
    def is_satisfied_by(self, order):
        raise NotImplementedError

    def __and__(self, other):
        return AndSpec(self, other)
    def __or__(self, other):
        return OrSpec(self, other)
    def __invert__(self):
        return NotSpec(self)

class AndSpec(Specification):
    def __init__(self, left, right):
        self.left, self.right = left, right
    def is_satisfied_by(self, order):
        return (self.left.is_satisfied_by(order)
                and self.right.is_satisfied_by(order))

class OrSpec(Specification):
    def __init__(self, left, right):
        self.left, self.right = left, right
    def is_satisfied_by(self, order):
        return (self.left.is_satisfied_by(order)
                or self.right.is_satisfied_by(order))

class NotSpec(Specification):
    def __init__(self, specification):
        self.specification = specification
    def is_satisfied_by(self, order):
        return not self.specification.is_satisfied_by(order)

class MinimumAmountSpec(Specification):
    def __init__(self, minimum_amount):
        self.minimum_amount = minimum_amount
    def is_satisfied_by(self, order):
        return order.total.amount > self.minimum_amount

class VIPCustomerSpec(Specification):
    def is_satisfied_by(self, order):
        return order.customer.is_vip

class MinimumUnitsSpec(Specification):
    def __init__(self, minimum_units):
        self.minimum_units = minimum_units
    def is_satisfied_by(self, order):
        return order.units >= self.minimum_units

class ActivePromotionSpec(Specification):
    def is_satisfied_by(self, order):
        return order.has_promotion

# Regla de descuento de 10 %:
ten_percent = (
    MinimumAmountSpec(Decimal("500"))
    & VIPCustomerSpec()
    & MinimumUnitsSpec(4)
    & ~ActivePromotionSpec()
)

#  Regla de 5 %: total > 5000 y SIN promoción.
five_percent = (
    MinimumAmountSpec(Decimal("5000"))
    & ~ActivePromotionSpec()
)

# Combina ambas reglas con OR.
discount_eligible = ten_percent | five_percent

# Si ambas se cumplen, aplica primero 10 %.
def discount_rate_for(order):
    if ten_percent.is_satisfied_by(order):
        return Decimal("0.10")
    if five_percent.is_satisfied_by(order):
        return Decimal("0.05")
    return Decimal("0")
