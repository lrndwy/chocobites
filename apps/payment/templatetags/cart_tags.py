from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def cart_item_count(context):
    cart = context['request'].session.get('cart', {})
    return sum(cart.values()) 
