    function saveToggleState(el) {
        var id = el.id;
        var isOpen = el.hasAttribute('open')?'open':'closed';
        //console.log(id, isOpen);
        window.localStorage.setItem('details-'+id, isOpen);
    }
    function setDetailOpenStatus(item, nonDefaults) {
        if (item.includes('details-')) {
            var id = item.split('details-')[1];
            var status = window.localStorage.getItem(item);
            if (status=='open' || nonDefaults.includes(id)) {
                elToSet = document.getElementById(id)
                if(elToSet) {
                    elToSet.setAttribute('open', true);
                } else {
                    console.log("setDetailOpenStatus: Could not find element: "+id)
                }                
            }
        }
    }
    // TODO: On initial GET (nav from UI, not refresh on view update), clear all the Open Status values. 
    // This may be trickier now that we filter extraneous parameters. 
    function initDetailsFromStorage(nonDefaults) {
        for (var i = 0; i < localStorage.length; i++) {
            setDetailOpenStatus(localStorage.key(i), nonDefaults);
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
            elToSkip = document.getElementById(id)
            if(elToSkip) {
                elToSkip.classList.add("skipFilter");
            } else {
                console.log("hideFilter: Could not find element: "+id)
            }
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
    function handleFacingSelection(evt) {
        var value;
        if(evt != null) {
            value = evt.target.value;
            console.log("Facing selected: "+value);
        } else {
            value = document.getElementById("id_facings").value;
            console.log("Initial facing selected: "+value);
        }
        showHideTopicsForFacing(value)
    }
    function hideAllOptionsNot(topicsSel, prefix) {
        var topic, i;

        for(i = 0; i < topicsSel.length; i++) {
            topic = topicsSel[i];
            if (topic.value.startsWith(prefix) || topic.value == "all") {
                topic.disabled = false;
            } else {
                topic.disabled = true;
            }
          }
        // When the facing changes and the topic was selected from another facing, revert topic to all
        if(!topicsSel.value.startsWith(prefix)) {
            topicsSel.selectedIndex = 0;  // Force selection back to "all"
        }
     

    }
    function showHideTopicsForFacing(facing) {
        const topicsSel = document.getElementById("id_topics")
        var topicsContainerDiv = document.querySelector("div.viewselect:has(select#id_topics)")
        if(facing == "all") {
            if(topicsSel != null) {
                // if not logged in, may elide the select element
                topicsSel.classList.add("skip")
                topicsSel.value = 'all';
            } else {
                topicsContainerDiv = document.querySelector("div.viewselect:has(label[for='id_topics'])")
                topicsContainerDiv.classList.add("skip")
            }
        } else {
            if(topicsContainerDiv == null) {
                // if not logged in, may elide the select element
                topicsContainerDiv = document.querySelector("div.viewselect:has(label[for='id_topics'])")
            }
            if(topicsContainerDiv == null) {
                console.log("Couldn't find: id_topics container div!");
            } else {
                topicsContainerDiv.classList.remove("skip");
            }
            topicsSel.classList.remove("skip");
            hideAllOptionsNot(topicsSel, facing+"_")
        }

    }
