---
layout: null
sitemap: false
---

{% assign counter = 0 %}
var documents = [
    {% for page in site.pages %}{% if page.search == true %}
    {
    "id": {{ counter }},
    "url": "{{ page.url | prepend: site.baseurl }}",
    "title": "{{ page.title | escape }}",
    "body": "{{ page.content | markdownify | strip_html | strip_newlines | escape }}"
    {% assign counter = counter | plus: 1 %}
    }, {% endif %}{% endfor %}{% for page in site.posts %}
    {
    "id": {{ counter }},
    "url": "{{ page.url | prepend: site.baseurl }}",
    "title": "{{ page.title | escape }}",
    "body": "{{ page.content | markdownify | strip_html | strip_newlines | escape }}"
    {% assign counter = counter | plus: 1 %}
    }
    {% if forloop.last %}{% else %}, {% endif %}{% endfor %}
    ];

var idx = lunr(function () {
    this.ref('id')
    this.field('title')
    this.field('body')

    documents.forEach(function (doc) {
        this.add(doc)
    }, this)
});

function lunr_search(term) {
    if(term) {
        $('#lunrsearchresults').show(400);
        $("body").addClass("modal-open");
        document.getElementById('lunrsearchresults').innerHTML = '<div id="resultsmodal" class="modal fade show d-block"  tabindex="-1" role="dialog" aria-labelledby="resultsmodal"> <div class="modal-dialog shadow-lg" role="document"> <div class="modal-content"> <div class="modal-header" id="modtit"> <button type="button" class="close" id="btnx" data-dismiss="modal" aria-label="Close"> &times; </button> </div> <div class="modal-body"> <ul class="mb-0"> </ul>    </div> <div class="modal-footer"><button id="btnx" type="button" class="btn btn-danger btn-sm" data-dismiss="modal">Schliessen</button></div></div> </div></div>';
        document.getElementById('modtit').innerHTML = "<h5 class='modal-title'>Suchergebnis für '" + term + "'</h5>" + document.getElementById('modtit').innerHTML;
        //put results on the screen.
        var results = idx.search(term);
        if(results.length>0){
            //console.log(idx.search(term));
            //if results
            for (var i = 0; i < results.length; i++) {
                // more statements
                var ref = results[i]['ref'];
                var url = documents[ref]['url'];
                var title = documents[ref]['title'];
                var body = documents[ref]['body'].substring(0,160)+'...';
                document.querySelectorAll('#lunrsearchresults ul')[0].innerHTML = document.querySelectorAll('#lunrsearchresults ul')[0].innerHTML + "<li class='lunrsearchresult'><a href='" + url + "'><span class='title'>" + title + "</span><br /><small><span class='body'>"+ body +"</span><br /><span class='url'>"+ url +"</span></small></a></li>";
            }
        } else {
            document.querySelectorAll('#lunrsearchresults ul')[0].innerHTML = "<li class='lunrsearchresult'>Leider keine Seiten gefunden.</li>";
        }
    }
    return false;
}
    
$(function() {
    $("#lunrsearchresults").on('click', '#btnx', function () {
        $('#lunrsearchresults').hide(5);
        $("body").removeClass("modal-open");
    });
});