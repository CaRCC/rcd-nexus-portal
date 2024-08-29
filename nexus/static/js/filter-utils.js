    function saveToggleState(el) {
        var id = el.id;
        var isOpen = el.hasAttribute('open')?'open':'closed';
        //console.log(id, isOpen);
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
    // TODO: On initial GET (nav from UI, not refresh on view update), clear all the Open Status values. 
    function initDetailsFromStorage() {
        for (var i = 0; i < localStorage.length; i++) {
            setDetailOpenStatus(localStorage.key(i));
        }
    }
    // Only callable when the detail is open. Find all the checkboxes under this and set them checked
    function setAllCheckboxState(id, checked) {
        // Get the options under the indicated element
        selector = "#"+id+" input[type=checkbox]";
        const nodeList = document.querySelectorAll(selector);
        for (let i = 0; i < nodeList.length; i++) {
          nodeList[i].checked = checked;
        }
    }
    function setAll(id) {
        setAllCheckboxState(id, true) 
    }
    function clearAll(id) {
        setAllCheckboxState(id, false) 
    }
    function hideFilter(id) {
        // Clear skipFilter from all the toplevel li items and set skipFilter on the passed one
        selector = '#filtertree ul.filter>li.skipFilter';
        const nodeList = document.querySelectorAll(selector);
        if(nodeList) {
            for (let i = 0; i < nodeList.length; i++) {
                nodeList[i].classList.remove("skipFilter");
            }
        }
        if(id) {
            document.getElementById(id).classList.add("skipFilter");
            // Reset the choices to all so we do not mess up the filtering
            setAll(id);
        }
    }
    function handleChartViewSelection(evt) {
        var value = evt.target.value;
        console.log("ChartView selected: "+value);
        hideFiltersForChartView(value)
    }
    function hideFiltersForChartView(view) {
        switch(view) {
            case "cc":
            case "pub_priv":
            case "mission":
            case "epscor":
            case "msi":
                toHide = "id_"+view+"_fli";
                break;
            default:
                toHide = "";    // Just clear any skipFilter classes
        }
        hideFilter(toHide);
    }
