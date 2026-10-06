// Car Service and Repair Management System - Client Scripts

document.addEventListener('DOMContentLoaded', function () {
    // 1. Set minimum booking date to today
    const bookingDateInput = document.getElementById('booking_date');
    if (bookingDateInput) {
        const today = new Date().toISOString().split('T')[0];
        bookingDateInput.setAttribute('min', today);
    }

    // 2. Auto-calculate Bill Total dynamically in billing forms
    const serviceChargeInput = document.getElementById('service_charge');
    const partsChargeInput = document.getElementById('parts_charge');
    const totalAmountInput = document.getElementById('total_amount');

    function calculateTotalBill() {
        if (serviceChargeInput && totalAmountInput) {
            const sc = parseFloat(serviceChargeInput.value) || 0;
            const pc = parseFloat(partsChargeInput ? partsChargeInput.value : 0) || 0;
            const total = sc + pc;
            totalAmountInput.value = total.toFixed(2);
        }
    }

    if (serviceChargeInput) {
        serviceChargeInput.addEventListener('input', calculateTotalBill);
    }
    if (partsChargeInput) {
        partsChargeInput.addEventListener('input', calculateTotalBill);
    }

    // 3. Dynamic price calculation when adding spare parts in repair
    const partSelect = document.getElementById('part_id');
    const partQty = document.getElementById('quantity_used');
    const unitPriceDisplay = document.getElementById('unit_price_display');
    const subtotalDisplay = document.getElementById('subtotal_display');

    function updatePartCost() {
        if (partSelect && partSelect.selectedIndex > 0) {
            const selectedOption = partSelect.options[partSelect.selectedIndex];
            const price = parseFloat(selectedOption.getAttribute('data-price')) || 0;
            const qty = parseInt(partQty ? partQty.value : 1) || 1;
            
            if (unitPriceDisplay) unitPriceDisplay.textContent = '₹' + price.toFixed(2);
            if (subtotalDisplay) subtotalDisplay.textContent = '₹' + (price * qty).toFixed(2);
        }
    }

    if (partSelect) {
        partSelect.addEventListener('change', updatePartCost);
    }
    if (partQty) {
        partQty.addEventListener('input', updatePartCost);
    }

    // 4. Confirm Deletions
    const deleteButtons = document.querySelectorAll('.confirm-delete');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function (e) {
            const itemName = this.getAttribute('data-item') || 'this item';
            if (!confirm(`Are you sure you want to delete ${itemName}? This action cannot be undone.`)) {
                e.preventDefault();
            }
        });
    });

    // 5. Auto dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });
});
