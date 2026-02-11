from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

@dataclass
class LineItem:
    sku: str
    category: str
    unit_price: float
    qty: int
    fragile: bool = False

@dataclass
class Invoice:
    invoice_id: str
    customer_id: str
    country: str
    membership: str
    coupon: Optional[str]
    items: List[LineItem]

class InvoiceService:
    # Configuration-driven approach to eliminate duplicate logic
    COUPON_RATES: Dict[str, float] = {
        "WELCOME10": 0.10,
        "VIP20": 0.20,
        "STUDENT5": 0.05
    }
    
    SHIPPING_CONFIG: Dict[str, Tuple[float, float]] = {
        "TH": (500, 60),
        "JP": (4000, 600),
        "US": (100, 15),      # First threshold
        "DEFAULT": (200, 25)
    }
    
    US_SHIPPING_TIERS: Tuple[Tuple[float, float], ...] = (
        (100, 15),
        (300, 8)
    )
    
    TAX_RATES: Dict[str, float] = {
        "TH": 0.07,
        "JP": 0.10,
        "US": 0.08,
        "DEFAULT": 0.05
    }
    
    MEMBERSHIP_DISCOUNTS: Dict[str, float] = {
        "gold": 0.03,
        "platinum": 0.05
    }

    def __init__(self) -> None:
        self._coupon_rate = self.COUPON_RATES

    def _validate(self, inv: Invoice) -> List[str]:
        problems: List[str] = []
        if inv is None:
            problems.append("Invoice is missing")
            return problems
        if not inv.invoice_id:
            problems.append("Missing invoice_id")
        if not inv.customer_id:
            problems.append("Missing customer_id")
        if not inv.items:
            problems.append("Invoice must contain items")
        for it in inv.items:
            if not it.sku:
                problems.append("Item sku is missing")
            if it.qty <= 0:
                problems.append(f"Invalid qty for {it.sku}")
            if it.unit_price < 0:
                problems.append(f"Invalid price for {it.sku}")
            if it.category not in ("book", "food", "electronics", "other"):
                problems.append(f"Unknown category for {it.sku}")
        return problems

    def _calculate_subtotal_and_fragile_fee(self, items: List[LineItem]) -> Tuple[float, float]:
        """Calculate subtotal and fragile handling fee."""
        subtotal = 0.0
        fragile_fee = 0.0
        for it in items:
            subtotal += it.unit_price * it.qty
            if it.fragile:
                fragile_fee += 5.0 * it.qty
        return subtotal, fragile_fee

    def _calculate_shipping(self, country: str, subtotal: float) -> float:
        """Calculate shipping cost based on country and subtotal."""
        if country == "US":
            for threshold, fee in self.US_SHIPPING_TIERS:
                if subtotal < threshold:
                    return fee
            return 0.0
        
        # Standard single-threshold logic for other countries
        config = self.SHIPPING_CONFIG.get(country, self.SHIPPING_CONFIG["DEFAULT"])
        threshold, fee = config
        return fee if subtotal < threshold else 0.0

    def _calculate_discount(self, inv: Invoice, subtotal: float, warnings: List[str]) -> float:
        """Calculate total discount from membership and coupon."""
        discount = 0.0
        
        # Membership discount
        if inv.membership in self.MEMBERSHIP_DISCOUNTS:
            discount += subtotal * self.MEMBERSHIP_DISCOUNTS[inv.membership]
        elif subtotal > 3000:
            discount += 20
        
        # Coupon discount
        if inv.coupon:
            code = inv.coupon.strip()
            if code in self.COUPON_RATES:
                discount += subtotal * self.COUPON_RATES[code]
            else:
                warnings.append("Unknown coupon")
        
        return discount

    def _calculate_tax(self, country: str, taxable_amount: float) -> float:
        """Calculate tax based on country."""
        rate = self.TAX_RATES.get(country, self.TAX_RATES["DEFAULT"])
        return taxable_amount * rate

    def compute_total(self, inv: Invoice) -> Tuple[float, List[str]]:
        warnings: List[str] = []
        problems = self._validate(inv)
        if problems:
            raise ValueError("; ".join(problems))

        subtotal, fragile_fee = self._calculate_subtotal_and_fragile_fee(inv.items)
        shipping = self._calculate_shipping(inv.country, subtotal)
        discount = self._calculate_discount(inv, subtotal, warnings)
        tax = self._calculate_tax(inv.country, subtotal - discount)

        total = max(0.0, subtotal + shipping + fragile_fee + tax - discount)
        
        if subtotal > 10000 and inv.membership not in ("gold", "platinum"):
            warnings.append("Consider membership upgrade")

        return total, warnings
