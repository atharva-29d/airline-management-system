document.addEventListener('DOMContentLoaded', async () => {

    // Sidebar navigation
    const sections = {
        loyaltyLink: 'loyaltyContent',
        bookTicketLink: 'bookTicketContent',
        myBookingsLink: 'myBookingsContent',
        cancelTicketLink: 'cancelTicketContent',
        profileSettingsLink: 'profileSettingsContent'
    };

    Object.keys(sections).forEach(linkId => {
        document.getElementById(linkId).addEventListener('click', () => {
            Object.values(sections).forEach(sec => document.getElementById(sec).classList.add('hidden'));
            document.getElementById(sections[linkId]).classList.remove('hidden');

            document.querySelectorAll('.sidebar-link').forEach(link => link.classList.remove('active'));
            document.getElementById(linkId).classList.add('active');

            if(linkId === 'myBookingsLink') loadBookings();
            if(linkId === 'cancelTicketLink') loadCancellableBookings();
            if(linkId === 'profileSettingsLink') loadProfile();
        });
    });

    // Flight Search
    const sourceSelect = document.getElementById('source');
    const destSelect = document.getElementById('destination');
    const resultsDiv = document.getElementById('flightResults');
    const form = document.getElementById('flightSearchForm');

    // Populate dropdowns
    try {
        const res = await fetch('/api/airports');
        const airports = await res.json();

        airports.forEach(a => {
            const option1 = document.createElement('option');
            option1.value = a.code;
            option1.textContent = `${a.city} (${a.code})`;
            sourceSelect.appendChild(option1);

            const option2 = document.createElement('option');
            option2.value = a.code;
            option2.textContent = `${a.city} (${a.code})`;
            destSelect.appendChild(option2);
        });
    } catch (err) {
        console.error('Error loading airports:', err);
    }

    // Handle advanced search with filters
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const source = sourceSelect.value;
        const dest = destSelect.value;
        const date = document.getElementById('flightDate').value;
        const airline = document.getElementById('airlineFilter').value;
        const minPrice = document.getElementById('minPrice').value || 0;
        const maxPrice = document.getElementById('maxPrice').value || 999999;
        const sortBy = document.getElementById('sortBy').value;

        resultsDiv.innerHTML = '<p class="text-gray-500 text-center py-8">Searching for flights...</p>';

        if (!source || !dest) {
            resultsDiv.innerHTML = '<p class="text-red-500 text-center">Please select both source and destination.</p>';
            return;
        }

        if (source === dest) {
            resultsDiv.innerHTML = '<p class="text-red-500 text-center">Source and destination cannot be the same.</p>';
            return;
        }

        try {
            // Use advanced search API
            const response = await fetch('/api/flights/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    source: source,
                    dest: dest,
                    date: date,
                    airline: airline,
                    min_price: minPrice,
                    max_price: maxPrice,
                    sort_by: sortBy
                })
            });

            const flights = await response.json();

            // Show results count
            document.getElementById('flightCount').textContent = flights.length;
            document.getElementById('resultsCount').classList.remove('hidden');

            // Show active filters
            let filterText = [];
            if (date) filterText.push(`Date: ${date}`);
            if (airline !== 'all') {
                const airlineName = document.querySelector(`#airlineFilter option[value="${airline}"]`).textContent;
                filterText.push(`Airline: ${airlineName}`);
            }
            if (minPrice > 0 || maxPrice < 999999) {
                filterText.push(`Price: ₹${minPrice} - ₹${maxPrice}`);
            }
            if (filterText.length > 0) {
                document.getElementById('filterDisplay').textContent = filterText.join(' | ');
                document.getElementById('activeFilters').classList.remove('hidden');
            }

            if (!flights.length) {
                resultsDiv.innerHTML = '<div class="col-span-2 text-center py-12"><p class="text-red-500 text-xl mb-2">😞 No flights found</p><p class="text-gray-600">Try adjusting your filters</p></div>';
                return;
            }

            resultsDiv.innerHTML = flights.map(f => {
                const duration = Math.floor(f.duration / 60) + 'h ' + (f.duration % 60) + 'm';
                return `
                    <div class="bg-white p-6 rounded-lg shadow-md hover:shadow-xl transition-shadow">
                        <div class="flex justify-between items-start mb-4">
                            <div>
                                <h3 class="text-xl font-bold text-gray-900">${f.airline}</h3>
                                <p class="text-gray-600">${f.flight_no}</p>
                            </div>
                            <div class="text-right">
                                <p class="text-sm text-gray-500">Starting from</p>
                                <p class="text-2xl font-bold text-red-600">₹${f.price_economy.toLocaleString()}</p>
                            </div>
                        </div>
                        
                        <div class="mb-4 py-3 border-t border-b border-gray-200">
                            <div class="flex justify-between items-center">
                                <div>
                                    <p class="text-lg font-semibold">${f.source}</p>
                                    <p class="text-sm text-gray-600">${new Date(f.departure_time).toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit'})}</p>
                                </div>
                                <div class="flex-1 mx-4">
                                    <div class="border-t-2 border-gray-300 relative">
                                        <span class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white px-2 text-xs text-gray-500">
                                            ${duration}
                                        </span>
                                    </div>
                                </div>
                                <div class="text-right">
                                    <p class="text-lg font-semibold">${f.destination}</p>
                                    <p class="text-sm text-gray-600">${new Date(f.arrival_time).toLocaleTimeString('en-IN', {hour: '2-digit', minute: '2-digit'})}</p>
                                </div>
                            </div>
                            <p class="text-center text-xs text-gray-500 mt-2">${new Date(f.departure_time).toLocaleDateString('en-IN', {weekday: 'short', day: 'numeric', month: 'short'})}</p>
                        </div>

                        <div class="space-y-2 mb-4">
                            <label class="flex items-center justify-between p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition">
                                <div class="flex items-center">
                                    <input type="radio" name="class_${f.flight_id}" value="economy" checked class="mr-3">
                                    <span class="font-medium">Economy</span>
                                </div>
                                <div class="text-right">
                                    <span class="font-bold text-gray-900">₹${f.price_economy.toLocaleString()}</span>
                                    <span class="text-xs text-gray-500 block">${f.available_seats_economy} seats</span>
                                </div>
                            </label>
                            
                            <label class="flex items-center justify-between p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition">
                                <div class="flex items-center">
                                    <input type="radio" name="class_${f.flight_id}" value="business" class="mr-3">
                                    <span class="font-medium">Business</span>
                                </div>
                                <div class="text-right">
                                    <span class="font-bold text-gray-900">₹${f.price_business.toLocaleString()}</span>
                                    <span class="text-xs text-gray-500 block">${f.available_seats_business} seats</span>
                                </div>
                            </label>
                            
                            <label class="flex items-center justify-between p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition">
                                <div class="flex items-center">
                                    <input type="radio" name="class_${f.flight_id}" value="first" class="mr-3">
                                    <span class="font-medium">First Class</span>
                                </div>
                                <div class="text-right">
                                    <span class="font-bold text-gray-900">₹${f.price_first.toLocaleString()}</span>
                                    <span class="text-xs text-gray-500 block">${f.available_seats_first} seats</span>
                                </div>
                            </label>
                        </div>

                        <button onclick="
                            const selectedClass = document.querySelector('input[name=class_${f.flight_id}]:checked').value;
                            window.location.href='/select-seat/${f.flight_id}?class=' + selectedClass;
                        " class="w-full py-3 px-4 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition transform hover:scale-105">
                            Select Seat & Book
                        </button>
                    </div>
                `;
            }).join("");

        } catch (err) {
            console.error(err);
            resultsDiv.innerHTML = '<p class="text-red-500 text-center py-8">Error fetching flights. Please try again later.</p>';
        }
    });

    // Quick search function for popular routes
    window.quickSearch = function(source, dest) {
        document.getElementById('source').value = source;
        document.getElementById('destination').value = dest;
        document.getElementById('flightSearchForm').dispatchEvent(new Event('submit'));
    };

    // Clear filters function
    window.clearFilters = function() {
        document.getElementById('flightDate').value = '';
        document.getElementById('airlineFilter').value = 'all';
        document.getElementById('minPrice').value = '';
        document.getElementById('maxPrice').value = '';
        document.getElementById('sortBy').value = 'price';
        document.getElementById('activeFilters').classList.add('hidden');
    };

    // Load bookings with PDF download
    async function loadBookings() {
        const upcomingContainer = document.getElementById('upcomingBookings');
        const pastContainer = document.getElementById('pastBookings');
        if (!upcomingContainer || !pastContainer) return;

        upcomingContainer.innerHTML = '<p class="text-gray-500 text-center">Loading...</p>';
        pastContainer.innerHTML = '<p class="text-gray-500 text-center">Loading...</p>';

        try {
            const response = await fetch('/api/bookings');
            const data = await response.json();

            upcomingContainer.innerHTML = data.upcoming.length ? data.upcoming.map(b => `
                <div class="bg-white rounded-lg shadow-md p-6 mb-4 hover:shadow-lg transition">
                    <div class="flex justify-between items-start mb-3">
                        <div>
                            <h3 class="text-lg font-bold text-gray-900">${b.source} → ${b.destination}</h3>
                            <p class="text-sm text-gray-600">${b.airline} - ${b.flight_no}</p>
                        </div>
                        <span class="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-semibold">
                            ${b.status}
                        </span>
                    </div>
                    <div class="grid grid-cols-2 gap-4 text-sm mb-4">
                        <div>
                            <p class="text-gray-500">Departure</p>
                            <p class="font-semibold">${new Date(b.departure_time).toLocaleString('en-IN')}</p>
                        </div>
                        <div>
                            <p class="text-gray-500">Arrival</p>
                            <p class="font-semibold">${new Date(b.arrival_time).toLocaleString('en-IN')}</p>
                        </div>
                        <div>
                            <p class="text-gray-500">PNR</p>
                            <p class="font-semibold text-red-600">${b.pnr}</p>
                        </div>
                        <div>
                            <p class="text-gray-500">Seat</p>
                            <p class="font-semibold">${b.seat_no || 'N/A'}</p>
                        </div>
                        <div>
                            <p class="text-gray-500">Class</p>
                            <p class="font-semibold capitalize">${b.class}</p>
                        </div>
                        <div>
                            <p class="text-gray-500">Price</p>
                            <p class="font-semibold">₹${b.price}</p>
                        </div>
                    </div>
                    <div class="flex gap-2">
                        <a href="/download-ticket/${b.booking_id}" target="_blank"
                           class="flex-1 py-2 px-4 bg-blue-600 text-white text-center rounded-lg hover:bg-blue-700 transition text-sm font-medium">
                            📄 Download Ticket
                        </a>
                        <button onclick="window.open('/download-ticket/${b.booking_id}', '_blank')"
                                class="flex-1 py-2 px-4 bg-green-600 text-white rounded-lg hover:bg-green-700 transition text-sm font-medium">
                            📧 View Ticket
                        </button>
                    </div>
                </div>
            `).join('') : '<p class="text-gray-500">No upcoming trips found.</p>';

            pastContainer.innerHTML = data.past.length ? data.past.map(b => `
                <div class="bg-gray-100 rounded-lg p-4 mb-2">
                    <p class="font-bold">${b.source} → ${b.destination}</p>
                    <p class="text-sm text-gray-500">Flight: ${b.airline} - ${b.flight_no}</p>
                    <p class="text-xs">Departure: ${new Date(b.departure_time).toLocaleString()}</p>
                    <p class="text-xs">PNR: ${b.pnr}</p>
                </div>
            `).join('') : '<p class="text-gray-500">No past trips found.</p>';

        } catch (err) {
            console.error(err);
            upcomingContainer.innerHTML = pastContainer.innerHTML = '<p class="text-red-500">Error loading bookings.</p>';
        }
    }

    // Load cancellable bookings
    async function loadCancellableBookings() {
        const container = document.getElementById('cancellableBookings');
        if (!container) return;

        container.innerHTML = '<p class="text-gray-500 text-center">Loading...</p>';

        try {
            const response = await fetch('/api/bookings');
            const data = await response.json();

            if (!data.upcoming.length) {
                container.innerHTML = '<p class="text-gray-500 text-center py-8">No bookings available to cancel.</p>';
                return;
            }

            container.innerHTML = data.upcoming.map(b => `
                <div class="bg-white rounded-lg shadow-md p-6 mb-4">
                    <div class="flex justify-between items-start">
                        <div class="flex-1">
                            <h3 class="text-lg font-bold text-gray-900 mb-2">${b.source} → ${b.destination}</h3>
                            <p class="text-sm text-gray-600">${b.airline} - ${b.flight_no}</p>
                            <p class="text-sm text-gray-600 mt-2">Departure: ${new Date(b.departure_time).toLocaleString()}</p>
                            <p class="text-sm text-gray-600">PNR: <span class="font-semibold text-red-600">${b.pnr}</span></p>
                        </div>
                        <button onclick="cancelBooking(${b.booking_id}, '${b.pnr}')" 
                                class="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition">
                            Cancel Booking
                        </button>
                    </div>
                </div>
            `).join('');

        } catch (err) {
            console.error(err);
            container.innerHTML = '<p class="text-red-500">Error loading bookings.</p>';
        }
    }

    // Make cancelBooking function globally available
    window.cancelBooking = async function(bookingId, pnr) {
        if (!confirm(`Are you sure you want to cancel booking ${pnr}?\n\nNote: Cancellation charges may apply.`)) {
            return;
        }

        try {
            const response = await fetch(`/cancel/${bookingId}`, {
                method: 'POST'
            });

            const result = await response.json();

            if (response.ok) {
                alert('✅ Booking cancelled successfully!');
                loadCancellableBookings();
            } else {
                alert('❌ ' + result.error);
            }

        } catch (err) {
            console.error(err);
            alert('Error cancelling booking');
        }
    };

    // Load profile data
    async function loadProfile() {
        try {
            const response = await fetch('/api/profile');
            const data = await response.json();

            document.getElementById('profile_username').value = data.username;
            document.getElementById('profile_email').value = data.email;
            document.getElementById('profile_phone').value = data.phone;
            document.getElementById('profile_miles').textContent = data.air_miles;

        } catch (err) {
            console.error(err);
            alert('Error loading profile data');
        }
    }

    // Handle profile update
    const profileForm = document.getElementById('profileUpdateForm');
    if (profileForm) {
        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const email = document.getElementById('profile_email').value;
            const phone = document.getElementById('profile_phone').value;

            try {
                const response = await fetch('/api/profile', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ email, phone })
                });

                const result = await response.json();

                if (response.ok) {
                    alert('✅ Profile updated successfully!');
                } else {
                    alert('❌ ' + result.error);
                }

            } catch (err) {
                console.error(err);
                alert('Error updating profile');
            }
        });
    }

});