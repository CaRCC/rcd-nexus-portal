    function saveToggleState(el) {
        var id = el.id;
        var isOpen = el.hasAttribute('open')?'open':'closed';
        console.log(id, isOpen);
        window.localStorage.setItem('details-'+id, isOpen);
    }
    function setDetailOpenStatus(item) {
        if (item.includes('details-')) {
            var id = item.split('details-')[1];
            var status = window.localStorage.getItem(item);
            if (status=='open') {
                document.getElementById(id).setAttribute('open', true);
            }
        }
    }
    function initDetailsFromStorage() {
        for (var i = 0; i < localStorage.length; i++) {
            setDetailOpenStatus(localStorage.key(i));
        }
    }
