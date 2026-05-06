from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from myapp.models import Department, DepartmentMember


class Command(BaseCommand):
    help = 'Assign all existing users to appropriate departments'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--default-department',
            type=str,
            help='Default department code for users (e.g., IT, HR)',
            default='IT'
        )
        
        parser.add_argument(
            '--role',
            type=str,
            help='Default role for users (MEMBER only)',
            default='MEMBER'
        )
    
    def handle(self, *args, **options):
        default_dept_code = options['default_department']
        default_role = 'MEMBER'
        
        try:
            default_dept = Department.objects.get(code=default_dept_code)
        except Department.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'Department with code "{default_dept_code}" not found!'
                )
            )
            return
        
        all_users = User.objects.all()
        assigned_count = 0
        
        for user in all_users:
                                                                   
            if user.is_superuser:
                continue

            if DepartmentMember.objects.filter(user=user).exists():
                continue
            
            DepartmentMember.objects.create(
                user=user,
                department=default_dept,
                role=default_role,
                can_assign_tickets=True,
                can_close_tickets=True,
                can_delete_tickets=False
            )
            
            assigned_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Assigned {user.username} to {default_dept.name}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully assigned {assigned_count} users to {default_dept.name} department'
            )
        )
