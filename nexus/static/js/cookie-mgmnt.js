    var SHOWN ="1";
    var HIDDEN = "0";
    var SHOW_HIDE_SUFFIX = "SH";
    var SHOW_HIDE_EXTRAS = "showEX";
    var COOKIE_LIFE = 7*24*60*60*1000;  // Save state for a week
    
    function setCookie(cname, shown) {
        const d = new Date();
        d.setTime(d.getTime() + COOKIE_LIFE);
        let expires = "expires="+ d.toUTCString();
        document.cookie = cname + "=" + shown + ";" + expires + ";path=/";
        //console.log("Set cookie for section: "+section+" to: "+shown);
    }

    function setExtraTopicsStateCookie(shown) {
        setCookie(SHOW_HIDE_EXTRAS, shown);
        console.log("Set Show/Hide Extras cookie: "+show);
    }

    function getStateCookie(name) {
        let decodedCookie = decodeURIComponent(document.cookie);
        let ca = decodedCookie.split(';');
        for(let i = 0; i <ca.length; i++) {
            let c = ca[i];
            let cpair = c.split('=');
            if (cpair[0].trim() == name) {
                var shown = cpair[1].trim();
                //console.log("Cookie found for section:"+section+" value: "+shown)
                return shown != HIDDEN;
            }
        }
        //console.log("No cookie found for showing section: "+section);
        return false;   // If can't find the cookie, don't show the section
    }