document.addEventListener('DOMContentLoaded', function() {
    const dateFilterInput = document.querySelector('input[type="date"][name="date"]');
    const searchForm = document.getElementById('changelist-search');

    if (dateFilterInput && searchForm) {
        const searchContainer = searchForm.querySelector('div');
        if (searchContainer) {
            // Remove hidden date input from search form to avoid duplicates
            const existingHidden = searchForm.querySelector('input[type="hidden"][name="date"]');
            if (existingHidden) {
                existingHidden.remove();
            }

            // Find the original container (the form in the sidebar)
            const originalForm = dateFilterInput.closest('form');
            const clearLinkDiv = originalForm ? originalForm.querySelector('div > a') : null;
            const clearLinkContainer = clearLinkDiv ? clearLinkDiv.parentNode : null;

            // Style the input
            dateFilterInput.style.width = 'auto';
            dateFilterInput.style.height = '30px'; // Slightly taller to match button
            dateFilterInput.style.padding = '4px 8px';
            dateFilterInput.style.marginLeft = '10px';
            dateFilterInput.style.verticalAlign = 'top';
            dateFilterInput.style.color = '#ffffff';
            dateFilterInput.style.backgroundColor = '#333';
            dateFilterInput.style.border = '1px solid #555';
            dateFilterInput.style.borderRadius = '4px';

            // Move input to search container
            searchContainer.appendChild(dateFilterInput);

            // Move clear link if exists
            if (clearLinkContainer) {
                clearLinkContainer.style.display = 'inline-block';
                clearLinkContainer.style.marginLeft = '10px';
                clearLinkContainer.style.verticalAlign = 'top';
                clearLinkContainer.style.marginTop = '6px'; // Align text
                searchContainer.appendChild(clearLinkContainer);
            }

            // Hide the original sidebar row
            if (originalForm) {
                const sidebarRow = originalForm.closest('li');
                if (sidebarRow) {
                    const sidebarTitle = sidebarRow.closest('ul').previousElementSibling;
                    if (sidebarTitle && sidebarTitle.tagName === 'H3') {
                        sidebarTitle.style.display = 'none';
                    }
                    sidebarRow.style.display = 'none';
                }
            }
        }
    }
});
