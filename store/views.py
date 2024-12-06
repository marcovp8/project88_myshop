from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .models import Product, Cart, CartItem, Order, OrderItem, Category
from django.http import Http404
from django.contrib import messages
from django.db.models import Q

# Функція для головної сторінки, яка відображає категорії
def home(request):
    categories = Category.objects.all()
    return render(request, 'store/home.html', {'categories': categories})

# Функція для відображення списку категорі
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'store/category_list.html', {'categories': categories})

# Функція для відображення каталогу товарів без фільтрації
def product_list(request):
    products = Product.objects.all()
    return render(request, 'store/product_list.html', {'products': products})

# Функція для відображення детальної інформації про товар
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})

# Функція для пошуку товарів
def search_products(request):
    query = request.GET.get('q')
    products = Product.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
    return render(request, 'store/product_list.html', {'products': products, 'query': query})

# Функція для реєстрації користувача
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'store/register.html', {'form': form})

@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'store/profile.html', {'orders': orders})

@login_required
def add_to_cart(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise Http404("Товар не найден")

    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if created:
        cart_item.quantity = 1
    else:
        cart_item.quantity += 1

    if cart_item.quantity > product.stock:
        messages.error(request, f"Недостатньо товару на складі. В наявності тільки {product.stock} шт.")
        return redirect('cart_view')

    cart_item.save()
    messages.success(request, "Товар успішно додано до кошика.")

    return redirect('cart_view')

@login_required
def cart_view(request):
    cart = Cart.objects.filter(user=request.user).first()
    if not cart:
        return render(request, 'store/cart_view.html', {'empty': True})

    cart_items = CartItem.objects.filter(cart=cart)
    total = sum(item.total_price() for item in cart_items)

    return render(request, 'store/cart_view.html', {'cart_items': cart_items, 'total': total})

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Товар був успішно видалений з кошика.")
    return redirect('cart_view')

@login_required
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    quantity = int(request.POST.get('quantity', 1))

    if quantity > cart_item.product.stock:
        messages.error(request, f"Недостатньо товару на складі. В наявності тільки {cart_item.product.stock} шт.")
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, "Кількість товару була успішно оновлена.")

    return redirect('cart_view')

@login_required
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()
    if not cart:
        return redirect('cart_view')

    insufficient_stock_items = []
    for item in CartItem.objects.filter(cart=cart):
        if item.quantity > item.product.stock:
            insufficient_stock_items.append(item)

    if insufficient_stock_items:
        for item in insufficient_stock_items:
            messages.error(request, f"Недостатньо товару на складі для {item.product.name}. В наявності тільки {item.product.stock} шт.")
        return redirect('cart_view')

    order = Order.objects.create(user=request.user)
    for item in CartItem.objects.filter(cart=cart):
        OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
        item.product.reduce_stock(item.quantity)

    cart.delete()

    messages.success(request, "Замовлення успішно оформлене!")
    return redirect('checkout_success')

@login_required
def checkout_success(request):
    return render(request, 'store/checkout_success.html')

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'store/order_history.html', {'orders': orders})

def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)
    return render(request, 'store/category_detail.html',
                  {'category': category, 'products': products})