from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except:
        return 0
    

@register.filter
def addition(value,arg):
    try:
        return float(value) + float(arg)
    except:
        return 0



@register.filter
def subtract(value,arg):
    try:
        return float(value) - float(arg)
    except:
        return 0