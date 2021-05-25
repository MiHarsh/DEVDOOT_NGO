
$(window).scroll(function(){
  var height = $(window).scrollTop();
  if ( height > 0 ) {
    $('.navbar-sticky').addClass('visible');
  } else {
    $('.navbar-sticky').removeClass('visible');
  }
  if (height > 260) {
    $('.gotop').fadeIn();
  }else {
    $('.gotop').fadeOut();
    }
 });


$('.navbar-collapse .nav-link:not(.dropdown-toggle)').click(function () {
  $('#collapsibleNavbar').collapse('hide');
});

$('.navbar-cross').click(function () {
  $('#collapsibleNavbar')[0].style.width = "0";
});

$('#collapsibleNavbar').on('hidden.bs.collapse', function () {
  $('#collapsibleNavbar')[0].style.removeProperty('width');
});
