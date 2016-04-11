"""XXX-Just a payment simulation"""

# XXX: implement external payment check

#Payment is ok. Set shopping cart is payed
context.SaleOrder_setShoppingCartBuyer()

#Finalize order and redirect
return context.SaleOrder_finalizeShopping()
