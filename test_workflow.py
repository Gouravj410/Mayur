import sys
import unittest
from app import app
from database.db import fetch_one, fetch_all

class CarServiceFlowTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_complete_demonstration_workflow(self):
        print("\n==========================================")
        print("STARTING COMPLETE DEMONSTRATION WORKFLOW TEST")
        print("==========================================")

        # 1. Test Public Pages
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'AutoCare', res.data)
        print("[PASS] Public Home Page: OK (200)")

        res = self.client.get('/services')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'General Service', res.data)
        print("[PASS] Public Services Page: OK (200)")

        # 2. Test Customer Registration
        test_email = 'rohit.sharma@example.com'
        reg_data = {
            'full_name': 'Rohit Sharma',
            'email': test_email,
            'phone': '9876501234',
            'address': 'Flat 304, Green Heights, Pune',
            'password': 'password123',
            'confirm_password': 'password123'
        }
        res = self.client.post('/register', data=reg_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        print("[PASS] Customer Registration: OK")

        # 3. Test Customer Login
        login_data = {
            'email': test_email,
            'password': 'password123'
        }
        res = self.client.post('/login', data=login_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Rohit Sharma', res.data)
        print("[PASS] Customer Login: OK (Session Established)")

        # 4. Test Customer Adds Vehicle
        veh_data = {
            'registration_number': 'MH-14-GH-9988',
            'brand': 'Hyundai',
            'model': 'Creta SX',
            'manufacturing_year': '2022',
            'fuel_type': 'Diesel',
            'vehicle_color': 'Phantom Black'
        }
        res = self.client.post('/vehicles/add', data=veh_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'MH-14-GH-9988', res.data)
        print("[PASS] Add Vehicle: OK (MH-14-GH-9988 Registered)")

        # Fetch vehicle ID from DB
        vehicle = fetch_one("SELECT id FROM vehicles WHERE registration_number = 'MH-14-GH-9988'")
        self.assertIsNotNone(vehicle)
        vehicle_id = vehicle['id']

        # 5. Customer Books a Service (General Service)
        service = fetch_one("SELECT id FROM services WHERE service_name = 'General Service'")
        service_id = service['id']
        booking_data = {
            'vehicle_id': vehicle_id,
            'service_id': service_id,
            'booking_date': '2026-10-15',
            'booking_time': '09:00 AM - 11:00 AM',
            'problem_description': '10,000 KM scheduled service plus slight brake squeak'
        }
        res = self.client.post('/bookings/book', data=booking_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Pending Approval', res.data)
        print("[PASS] Book Service: OK (Booking created with Pending status)")

        # Fetch booking id
        booking = fetch_one("SELECT id FROM bookings WHERE vehicle_id = %s ORDER BY id DESC", (vehicle_id,))
        self.assertIsNotNone(booking)
        booking_id = booking['id']

        # Logout Customer
        self.client.get('/logout')
        print("[PASS] Customer Logout: OK")

        # 6. Admin Login
        admin_data = {
            'email': 'admin@carservice.com',
            'password': 'admin123'
        }
        res = self.client.post('/admin/login', data=admin_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Admin Panel', res.data)
        print("[PASS] Admin Login: OK (Admin privileges granted)")

        # 7. Admin Approves Booking
        status_data = {
            'booking_status': 'Approved',
            'admin_notes': 'Assigned to Bay 2 technician team.'
        }
        res = self.client.post(f'/bookings/admin/{booking_id}/status', data=status_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        print("[PASS] Admin Approves Booking: OK (Repair record automatically initialized)")

        # Verify Repair Record
        repair = fetch_one("SELECT id FROM repairs WHERE booking_id = %s", (booking_id,))
        self.assertIsNotNone(repair)
        repair_id = repair['id']

        # 8. Admin Updates Repair Job to 'In Progress' with Diagnosis
        repair_update_data = {
            'diagnosis': 'Front brake pads worn out down to 2mm. Engine oil dirty.',
            'work_performed': 'Brake pads removed and replaced. Engine oil flushed.',
            'repair_notes': 'Customer requested synthetic 5W-30 oil.',
            'repair_status': 'In Progress'
        }
        res = self.client.post(f'/repairs/{repair_id}/edit', data=repair_update_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        print("[PASS] Admin Updates Repair Job: OK (Status: In Progress)")

        # 9. Admin Adds Spare Parts (Brake Pad and Engine Oil)
        part1 = fetch_one("SELECT id, quantity FROM spare_parts WHERE part_number = 'BRK-PAD-FR01'")
        initial_stock = part1['quantity']
        res = self.client.post(f'/repairs/{repair_id}/add-part', data={'part_id': part1['id'], 'quantity_used': 1}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify stock was deducted
        part1_after = fetch_one("SELECT quantity FROM spare_parts WHERE id = %s", (part1['id'],))
        self.assertEqual(part1_after['quantity'], initial_stock - 1)
        print(f"[PASS] Spare Part Stock Deduction: OK (Stock reduced from {initial_stock} to {part1_after['quantity']})")

        # 10. Admin Marks Repair as 'Completed'
        res = self.client.post(f'/repairs/{repair_id}/edit', data={
            'diagnosis': 'Front brake pads worn out down to 2mm. Engine oil dirty.',
            'work_performed': 'Brake pads replaced, calipers greased, road test successful.',
            'repair_notes': 'Vehicle ready for customer pickup.',
            'repair_status': 'Completed'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        print("[PASS] Repair Marked as Completed: OK (Booking status synchronized to Completed)")

        # 11. Verify Bill Calculation
        bill = fetch_one("SELECT * FROM bills WHERE booking_id = %s", (booking_id,))
        self.assertIsNotNone(bill)
        expected_total = float(bill['service_charge']) + float(bill['parts_charge'])
        self.assertAlmostEqual(float(bill['total_amount']), expected_total)
        print(f"[PASS] Bill Calculation Verified: Labor={bill['service_charge']} + Parts={bill['parts_charge']} = Total {bill['total_amount']}")

        # 12. Admin Records Payment (UPI)
        pay_data = {
            'amount': bill['total_amount'],
            'payment_method': 'UPI',
            'transaction_reference': 'UPI-REF-9988776655'
        }
        res = self.client.post(f'/billing/{bill["id"]}/pay', data=pay_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify Bill is Paid
        bill_after = fetch_one("SELECT payment_status FROM bills WHERE id = %s", (bill['id'],))
        self.assertEqual(bill_after['payment_status'], 'Paid')
        print("[PASS] Payment Record: OK (Bill marked Paid via UPI)")

        # 13. Admin Reviews Reports
        res = self.client.get('/reports/?tab=payments')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Invoicing', res.data)
        print("[PASS] Admin Reports Dashboard: OK")

        # Admin Logout
        self.client.get('/logout')

        # 14. Customer Logs in to view Completed Service, Invoice, and Vehicle History
        self.client.post('/login', data=login_data, follow_redirects=True)
        
        # Check Booking Details View
        res = self.client.get(f'/bookings/{booking_id}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Service Completed', res.data)
        print("[PASS] Customer View Completed Booking: OK")

        # Check Official Invoice View
        res = self.client.get(f'/billing/{bill["id"]}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Tax Invoice', res.data)
        self.assertIn(b'Paid', res.data)
        print("[PASS] Customer Official Tax Invoice View: OK")

        # Check Vehicle Service History Log
        res = self.client.get(f'/history/vehicle/{vehicle_id}')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'MH-14-GH-9988', res.data)
        print("[PASS] Customer Vehicle Permanent Service History: OK")

        print("==========================================")
        print("ALL WORKFLOW TESTS PASSED 100% SUCCESSFULLY!")
        print("==========================================")

if __name__ == '__main__':
    unittest.main()
