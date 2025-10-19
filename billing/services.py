import stripe
import requests
import json
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from .models import (
    SubscriptionPlan, UserSubscription, Payment, 
    BankAccount, Invoice, PaymentNotification
)


class StripePaymentService:
    """Stripe payment processing service"""
    
    def __init__(self):
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    
    def create_payment_intent(self, user, subscription, amount, currency='USD'):
        """Create a Stripe payment intent"""
        try:
            # Create payment record
            payment = Payment.objects.create(
                user=user,
                subscription=subscription,
                amount=amount,
                currency=currency,
                payment_method='stripe',
                status='pending'
            )
            
            # Create Stripe payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency.lower(),
                automatic_payment_methods={
                    'enabled': True,
                },
                metadata={
                    'payment_id': str(payment.id),
                    'user_id': str(user.id),
                    'subscription_id': str(subscription.id),
                }
            )
            
            # Update payment with Stripe ID
            payment.stripe_payment_intent_id = intent.id
            payment.save()
            
            return {
                'success': True,
                'payment_id': payment.id,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_subscription(self, user, plan):
        """Create a Stripe subscription"""
        try:
            # Create or get Stripe customer
            customer = self._get_or_create_customer(user)
            
            # Create Stripe price if not exists
            price = self._get_or_create_price(plan)
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': price.id}],
                metadata={
                    'user_id': str(user.id),
                    'plan_id': str(plan.id),
                }
            )
            
            # Create local subscription record
            user_subscription = UserSubscription.objects.create(
                user=user,
                plan=plan,
                status='pending',
                stripe_subscription_id=subscription.id
            )
            
            return {
                'success': True,
                'subscription_id': user_subscription.id,
                'stripe_subscription_id': subscription.id,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_or_create_customer(self, user):
        """Get or create Stripe customer"""
        try:
            # Try to find existing customer
            customers = stripe.Customer.list(email=user.email, limit=1)
            if customers.data:
                return customers.data[0]
            
            # Create new customer
            return stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}",
                metadata={'user_id': str(user.id)}
            )
        except Exception:
            raise
    
    def _get_or_create_price(self, plan):
        """Get or create Stripe price"""
        price_id = f"price_{plan.name.lower().replace(' ', '_')}_{plan.billing_period}"
        
        try:
            # Try to retrieve existing price
            return stripe.Price.retrieve(price_id)
        except stripe.error.InvalidRequestError:
            # Create new price
            interval_map = {
                'monthly': 'month',
                'annual': 'year',
                'decade': 'year'  # Will handle decade separately
            }
            
            if plan.billing_period == 'decade':
                # For decade, create a one-time price
                return stripe.Price.create(
                    id=price_id,
                    unit_amount=int(plan.price * 100),
                    currency='usd',
                    product_data={'name': f"{plan.name} - {plan.get_billing_period_display()}"}
                )
            else:
                return stripe.Price.create(
                    id=price_id,
                    unit_amount=int(plan.price * 100),
                    currency='usd',
                    recurring={'interval': interval_map[plan.billing_period]},
                    product_data={'name': f"{plan.name} - {plan.get_billing_period_display()}"}
                )
    
    def handle_webhook(self, payload, sig_header):
        """Handle Stripe webhooks"""
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            return {'success': False, 'error': 'Invalid payload'}
        except stripe.error.SignatureVerificationError:
            return {'success': False, 'error': 'Invalid signature'}
        
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            self._handle_payment_success(event['data']['object'])
        elif event['type'] == 'payment_intent.payment_failed':
            self._handle_payment_failed(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            self._handle_subscription_payment(event['data']['object'])
        
        return {'success': True}
    
    def _handle_payment_success(self, payment_intent):
        """Handle successful payment"""
        try:
            payment = Payment.objects.get(
                stripe_payment_intent_id=payment_intent['id']
            )
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.save()
            
            # Activate subscription
            if payment.subscription:
                payment.subscription.status = 'active'
                payment.subscription.save()
                
        except Payment.DoesNotExist:
            pass
    
    def _handle_payment_failed(self, payment_intent):
        """Handle failed payment"""
        try:
            payment = Payment.objects.get(
                stripe_payment_intent_id=payment_intent['id']
            )
            payment.status = 'failed'
            payment.save()
        except Payment.DoesNotExist:
            pass


class PaystackPaymentService:
    """Paystack payment processing service"""
    
    def __init__(self):
        self.secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')
        self.base_url = 'https://api.paystack.co'
    
    def initialize_payment(self, user, subscription, amount, currency='NGN'):
        """Initialize Paystack payment"""
        try:
            # Create payment record
            payment = Payment.objects.create(
                user=user,
                subscription=subscription,
                amount=amount,
                currency=currency,
                payment_method='paystack',
                status='pending'
            )
            
            # Initialize Paystack payment
            url = f"{self.base_url}/transaction/initialize"
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
                'Content-Type': 'application/json',
            }
            
            data = {
                'email': user.email,
                'amount': int(amount * 100),  # Convert to kobo
                'currency': currency,
                'reference': str(payment.id),
                'callback_url': getattr(settings, 'PAYSTACK_CALLBACK_URL', ''),
                'metadata': {
                    'payment_id': str(payment.id),
                    'user_id': str(user.id),
                    'subscription_id': str(subscription.id),
                }
            }
            
            response = requests.post(url, headers=headers, json=data)
            result = response.json()
            
            if result.get('status'):
                payment.paystack_reference = result['data']['reference']
                payment.save()
                
                return {
                    'success': True,
                    'payment_id': payment.id,
                    'authorization_url': result['data']['authorization_url'],
                    'reference': result['data']['reference']
                }
            else:
                return {'success': False, 'error': result.get('message', 'Payment initialization failed')}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify_payment(self, reference):
        """Verify Paystack payment"""
        try:
            url = f"{self.base_url}/transaction/verify/{reference}"
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
            }
            
            response = requests.get(url, headers=headers)
            result = response.json()
            
            if result.get('status') and result['data']['status'] == 'success':
                # Update payment status
                try:
                    payment = Payment.objects.get(paystack_reference=reference)
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                    payment.save()
                    
                    # Activate subscription
                    if payment.subscription:
                        payment.subscription.status = 'active'
                        payment.subscription.save()
                    
                    return {'success': True, 'payment': payment}
                except Payment.DoesNotExist:
                    return {'success': False, 'error': 'Payment not found'}
            else:
                return {'success': False, 'error': 'Payment verification failed'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def handle_webhook(self, payload, signature):
        """Handle Paystack webhooks"""
        # Verify webhook signature
        computed_signature = self._compute_signature(payload)
        
        if signature != computed_signature:
            return {'success': False, 'error': 'Invalid signature'}
        
        event = json.loads(payload)
        
        if event['event'] == 'charge.success':
            self._handle_charge_success(event['data'])
        elif event['event'] == 'subscription.create':
            self._handle_subscription_create(event['data'])
        
        return {'success': True}
    
    def _compute_signature(self, payload):
        """Compute Paystack webhook signature"""
        import hmac
        import hashlib
        
        return hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha512
        ).hexdigest()
    
    def _handle_charge_success(self, data):
        """Handle successful charge"""
        reference = data.get('reference')
        if reference:
            self.verify_payment(reference)


class BankTransferService:
    """Bank transfer payment processing"""
    
    def create_bank_payment(self, user, subscription, amount, currency, bank_account):
        """Create bank transfer payment"""
        try:
            payment = Payment.objects.create(
                user=user,
                subscription=subscription,
                amount=amount,
                currency=currency,
                payment_method='bank_transfer',
                status='pending',
                metadata={
                    'bank_account_id': bank_account.id,
                    'bank_name': bank_account.bank_name,
                    'account_number': bank_account.account_number,
                }
            )
            
            return {
                'success': True,
                'payment_id': payment.id,
                'bank_details': {
                    'bank_name': bank_account.bank_name,
                    'account_number': bank_account.account_number,
                    'account_name': bank_account.name,
                    'routing_number': bank_account.routing_number,
                    'swift_code': bank_account.swift_code,
                    'iban': bank_account.iban,
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def confirm_bank_payment(self, payment_id, bank_reference):
        """Confirm bank transfer payment (manual verification)"""
        try:
            payment = Payment.objects.get(id=payment_id)
            payment.bank_reference = bank_reference
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.save()
            
            # Activate subscription
            if payment.subscription:
                payment.subscription.status = 'active'
                payment.subscription.save()
            
            return {'success': True, 'payment': payment}
        except Payment.DoesNotExist:
            return {'success': False, 'error': 'Payment not found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class SubscriptionService:
    """Subscription management service"""
    
    def get_available_plans(self):
        """Get all available subscription plans"""
        return SubscriptionPlan.objects.filter(is_active=True)
    
    def get_plan_comparison(self):
        """Get plan comparison data with savings calculations"""
        plans = self.get_available_plans()
        comparison = {}
        
        for plan in plans:
            if plan.name not in comparison:
                comparison[plan.name] = {}
            
            comparison[plan.name][plan.billing_period] = {
                'id': plan.id,
                'price': plan.price,
                'monthly_equivalent': plan.monthly_equivalent_price,
                'savings': plan.savings_amount,
                'discount_percentage': plan.discount_percentage,
                'features': plan.features,
                'description': plan.description,
            }
        
        return comparison
    
    def check_subscription_status(self, user):
        """Check user's subscription status"""
        try:
            subscription = UserSubscription.objects.get(user=user)
            return {
                'has_subscription': True,
                'subscription': subscription,
                'is_active': subscription.is_active,
                'days_remaining': subscription.days_remaining,
                'plan': subscription.plan,
            }
        except UserSubscription.DoesNotExist:
            return {
                'has_subscription': False,
                'subscription': None,
                'is_active': False,
                'days_remaining': 0,
                'plan': None,
            }
    
    def cancel_subscription(self, user):
        """Cancel user's subscription"""
        try:
            subscription = UserSubscription.objects.get(user=user)
            subscription.status = 'cancelled'
            subscription.auto_renew = False
            subscription.save()
            
            # Cancel external subscriptions
            if subscription.stripe_subscription_id:
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
            
            return {'success': True, 'subscription': subscription}
        except UserSubscription.DoesNotExist:
            return {'success': False, 'error': 'No active subscription found'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class InvoiceService:
    """Invoice generation and management"""
    
    def generate_invoice(self, payment, tax_rate=0):
        """Generate invoice for payment"""
        try:
            # Calculate due date (7 days from issue)
            from datetime import timedelta
            due_date = timezone.now() + timedelta(days=7)
            
            invoice = Invoice.objects.create(
                payment=payment,
                issue_date=timezone.now(),
                due_date=due_date,
                subtotal=payment.amount,
                tax_rate=tax_rate,
            )
            
            return {'success': True, 'invoice': invoice}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_invoice_pdf(self, invoice_id):
        """Generate PDF for invoice (placeholder for actual PDF generation)"""
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            # Here you would integrate with a PDF generation library
            # like ReportLab or WeasyPrint
            return {'success': True, 'invoice': invoice}
        except Invoice.DoesNotExist:
            return {'success': False, 'error': 'Invoice not found'}
