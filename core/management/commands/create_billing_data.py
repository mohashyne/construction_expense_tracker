from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from billing.models import SubscriptionPlan, UserSubscription, Payment, BankAccount
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create sample billing data including subscription plans and payments'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating billing data...'))
        
        # Create subscription plans
        self.create_subscription_plans()
        
        # Create bank accounts
        self.create_bank_accounts()
        
        # Create subscriptions and payments for test users
        self.create_user_subscriptions()
        
        self.stdout.write(self.style.SUCCESS('\n✅ Billing data created successfully!'))
    
    def create_subscription_plans(self):
        """Create subscription plans with pricing tiers"""
        plans_data = [
            # Basic Plan
            {
                'name': 'Basic',
                'billing_period': 'monthly',
                'price': Decimal('29.99'),
                'discount_percentage': Decimal('0'),
                'features': [
                    'Up to 5 projects',
                    'Basic expense tracking',
                    'Email support',
                    '1 GB storage'
                ],
                'description': 'Perfect for small contractors and freelancers'
            },
            {
                'name': 'Basic',
                'billing_period': 'annual',
                'price': Decimal('299.99'),  # 2 months free
                'discount_percentage': Decimal('16.67'),
                'features': [
                    'Up to 5 projects',
                    'Basic expense tracking',
                    'Email support',
                    '1 GB storage',
                    'Annual reporting'
                ],
                'description': 'Basic plan with 2 months free - save 16%!'
            },
            {
                'name': 'Basic',
                'billing_period': 'decade',
                'price': Decimal('2399.99'),  # 2 years free
                'discount_percentage': Decimal('20'),
                'features': [
                    'Up to 5 projects',
                    'Basic expense tracking',
                    'Priority support',
                    '1 GB storage',
                    'Annual reporting',
                    'Lifetime updates'
                ],
                'description': 'Basic plan for 10 years - save 20%!'
            },
            
            # Professional Plan
            {
                'name': 'Professional',
                'billing_period': 'monthly',
                'price': Decimal('59.99'),
                'discount_percentage': Decimal('0'),
                'features': [
                    'Unlimited projects',
                    'Advanced expense tracking',
                    'Team collaboration',
                    'Priority support',
                    '10 GB storage',
                    'Custom reports'
                ],
                'description': 'Ideal for growing construction companies'
            },
            {
                'name': 'Professional',
                'billing_period': 'annual',
                'price': Decimal('599.99'),  # 2 months free
                'discount_percentage': Decimal('16.67'),
                'features': [
                    'Unlimited projects',
                    'Advanced expense tracking',
                    'Team collaboration',
                    'Priority support',
                    '10 GB storage',
                    'Custom reports',
                    'Annual analytics'
                ],
                'description': 'Professional plan with 2 months free - save 16%!'
            },
            {
                'name': 'Professional',
                'billing_period': 'decade',
                'price': Decimal('4799.99'),  # 2 years free
                'discount_percentage': Decimal('20'),
                'features': [
                    'Unlimited projects',
                    'Advanced expense tracking',
                    'Team collaboration',
                    '24/7 phone support',
                    '10 GB storage',
                    'Custom reports',
                    'Advanced analytics',
                    'Priority features'
                ],
                'description': 'Professional plan for 10 years - save 20%!'
            },
            
            # Enterprise Plan
            {
                'name': 'Enterprise',
                'billing_period': 'monthly',
                'price': Decimal('99.99'),
                'discount_percentage': Decimal('0'),
                'features': [
                    'Unlimited everything',
                    'Advanced analytics',
                    'Custom integrations',
                    'Dedicated support',
                    '100 GB storage',
                    'White-label options',
                    'API access'
                ],
                'description': 'Complete solution for large enterprises'
            },
            {
                'name': 'Enterprise',
                'billing_period': 'annual',
                'price': Decimal('999.99'),  # 2 months free
                'discount_percentage': Decimal('16.67'),
                'features': [
                    'Unlimited everything',
                    'Advanced analytics',
                    'Custom integrations',
                    'Dedicated account manager',
                    '100 GB storage',
                    'White-label options',
                    'API access',
                    'Custom training'
                ],
                'description': 'Enterprise plan with 2 months free - save 16%!'
            },
            {
                'name': 'Enterprise',
                'billing_period': 'decade',
                'price': Decimal('7999.99'),  # 2 years free
                'discount_percentage': Decimal('20'),
                'features': [
                    'Unlimited everything',
                    'Advanced analytics',
                    'Custom integrations',
                    'Dedicated account manager',
                    'Unlimited storage',
                    'White-label options',
                    'API access',
                    'On-premise option',
                    'Lifetime support'
                ],
                'description': 'Enterprise plan for 10 years - save 20%!'
            }
        ]
        
        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                billing_period=plan_data['billing_period'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(f'Created plan: {plan.name} - {plan.get_billing_period_display()}')
    
    def create_bank_accounts(self):
        """Create sample bank accounts for receiving payments"""
        accounts_data = [
            {
                'name': 'ConstructPro Business Account',
                'account_type': 'local',
                'bank_name': 'First National Bank',
                'account_number': '1234567890',
                'routing_number': '987654321',
                'currency': 'USD',
                'is_active': True
            },
            {
                'name': 'ConstructPro International',
                'account_type': 'international',
                'bank_name': 'Global Business Bank',
                'account_number': '0987654321',
                'swift_code': 'GBBKUS33',
                'iban': 'US12GBBK00009876543210',
                'currency': 'USD',
                'is_active': True
            },
            {
                'name': 'ConstructPro Nigeria',
                'account_type': 'local',
                'bank_name': 'Zenith Bank',
                'account_number': '2100123456',
                'currency': 'NGN',
                'is_active': True
            }
        ]
        
        for account_data in accounts_data:
            account, created = BankAccount.objects.get_or_create(
                name=account_data['name'],
                defaults=account_data
            )
            if created:
                self.stdout.write(f'Created bank account: {account.name}')
    
    def create_user_subscriptions(self):
        """Create subscriptions and payments for test users"""
        try:
            # Get test users
            company_user = User.objects.get(username='buildtech_admin')
            individual_user = User.objects.get(username='john_contractor')
            
            # Get subscription plans
            company_plan = SubscriptionPlan.objects.get(name='Professional', billing_period='annual')
            individual_plan = SubscriptionPlan.objects.get(name='Basic', billing_period='monthly')
            
            # Create company subscription
            company_subscription = UserSubscription.objects.create(
                user=company_user,
                plan=company_plan,
                status='active',
                start_date=timezone.now() - timedelta(days=30),  # Started 30 days ago
                end_date=timezone.now() + timedelta(days=335)   # 11 months remaining
            )
            
            # Create individual subscription
            individual_subscription = UserSubscription.objects.create(
                user=individual_user,
                plan=individual_plan,
                status='active',
                start_date=timezone.now() - timedelta(days=15),  # Started 15 days ago
                end_date=timezone.now() + timedelta(days=15)    # 15 days remaining
            )
            
            # Create completed payment for company
            Payment.objects.create(
                user=company_user,
                subscription=company_subscription,
                amount=company_plan.price,
                currency='USD',
                payment_method='stripe',
                status='completed',
                created_at=timezone.now() - timedelta(days=30),
                completed_at=timezone.now() - timedelta(days=30),
                stripe_payment_intent_id='pi_test_company_payment',
                metadata={
                    'plan_name': company_plan.name,
                    'billing_period': company_plan.billing_period,
                    'payment_completed': True
                }
            )
            
            # Create completed payment for individual
            Payment.objects.create(
                user=individual_user,
                subscription=individual_subscription,
                amount=individual_plan.price,
                currency='USD',
                payment_method='paystack',
                status='completed',
                created_at=timezone.now() - timedelta(days=15),
                completed_at=timezone.now() - timedelta(days=15),
                paystack_reference='ref_test_individual_payment',
                metadata={
                    'plan_name': individual_plan.name,
                    'billing_period': individual_plan.billing_period,
                    'payment_completed': True
                }
            )
            
            self.stdout.write('✅ Created subscriptions and payments for test users')
            self.stdout.write(f'Company user: {company_user.username} - {company_plan.name} (Annual)')
            self.stdout.write(f'Individual user: {individual_user.username} - {individual_plan.name} (Monthly)')
            
        except User.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f'Test user not found: {e}'))
        except SubscriptionPlan.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f'Subscription plan not found: {e}'))
