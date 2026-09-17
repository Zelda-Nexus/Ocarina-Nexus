(function(){
  // ---- Mobile nav ----
  var toggle = document.getElementById('navToggle');
  var links = document.getElementById('navLinks');
  toggle.addEventListener('click', function(){
    var open = links.classList.toggle('open');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  links.querySelectorAll('a').forEach(function(a){
    a.addEventListener('click', function(){ links.classList.remove('open'); toggle.setAttribute('aria-expanded','false'); });
  });

  // ---- Scrollspy ----
  var navAnchors = Array.from(links.querySelectorAll('a'));
  var sections = navAnchors.map(function(a){ return document.querySelector(a.getAttribute('href')); }).filter(Boolean);
  function onScroll(){
    var pos = window.scrollY + 140;
    var current = sections[0];
    sections.forEach(function(sec){ if(sec.offsetTop <= pos) current = sec; });
    navAnchors.forEach(function(a){ a.classList.toggle('active', current && a.getAttribute('href') === '#' + current.id); });
  }
  window.addEventListener('scroll', onScroll, {passive:true});
  onScroll();

  // ---- Reveal on scroll (never starts fully hidden) ----
  var reveals = document.querySelectorAll('.reveal');
  if('IntersectionObserver' in window){
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } });
    }, {threshold:.2});
    reveals.forEach(function(el){ io.observe(el); });
  } else {
    reveals.forEach(function(el){ el.classList.add('in'); });
  }

  // ---- Intro tagline reveal ----
  var introLines = document.querySelectorAll('.intro-line');
  if('IntersectionObserver' in window && introLines.length){
    var ioIntro = new IntersectionObserver(function(entries){
      entries.forEach(function(e){ if(e.isIntersecting){ introLines.forEach(function(l){ l.classList.add('in'); }); ioIntro.disconnect(); } });
    }, {threshold:.4});
    ioIntro.observe(document.getElementById('intro'));
  } else {
    introLines.forEach(function(l){ l.classList.add('in'); });
  }

  // ---- Hyrule mosaic triangular reveal ----
  var mosaic = document.querySelector('.mosaic');
  if(mosaic && 'IntersectionObserver' in window){
    var ioMosaic = new IntersectionObserver(function(entries){
      entries.forEach(function(e){ if(e.isIntersecting){ mosaic.classList.add('revealed'); ioMosaic.disconnect(); } });
    }, {threshold:.35});
    ioMosaic.observe(mosaic);
  } else if(mosaic){
    mosaic.classList.add('revealed');
  }

  // ---- Auto-play/pause videos only while visible (perf) ----
  var lazyVideos = document.querySelectorAll('video[data-autoplay]');
  if('IntersectionObserver' in window && lazyVideos.length){
    var ioVideo = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        var v = e.target;
        if(e.isIntersecting){ v.play().catch(function(){}); }
        else { v.pause(); }
      });
    }, {threshold:.3});
    lazyVideos.forEach(function(v){ ioVideo.observe(v); });
  }

  // ---- Carousel factory ----
  function makeCarousel(root){
    var track = root.querySelector('.carousel-track');
    var slides = Array.from(track.children);
    var dotsWrap = root.querySelector('.dots');
    var index = 0;
    slides.forEach(function(_, i){
      var d = document.createElement('button');
      d.className = 'dot' + (i === 0 ? ' active' : '');
      d.setAttribute('role','tab');
      d.setAttribute('aria-label','Aller à la diapositive ' + (i+1));
      d.addEventListener('click', function(){ go(i); });
      dotsWrap.appendChild(d);
    });
    var dots = Array.from(dotsWrap.children);
    function go(i){
      index = (i + slides.length) % slides.length;
      track.style.transform = 'translateX(-' + (index*100) + '%)';
      dots.forEach(function(d,di){ d.classList.toggle('active', di===index); });
      slides.forEach(function(s, si){
        var v = s.querySelector('video');
        if(!v) return;
        if(si === index){ v.play().catch(function(){}); } else { v.pause(); }
      });
    }
    root.querySelectorAll('.carousel-arrow').forEach(function(btn){
      btn.addEventListener('click', function(){ go(index + parseInt(btn.dataset.dir,10)); });
    });
    go(0);
  }
  document.querySelectorAll('.carousel').forEach(makeCarousel);

  // ---- Age toggle ----
  var ageData = {
    child: {
      desc: "Sans fée pour le guider jusqu'à ce que Navi le trouve, l'enfant Kokiri explore les clairières et les temples à hauteur de racines — vif, discret, sous-estimé.",
      weapon: 'Épée Kokiri', shield: 'Bouclier Deku', terrain: 'Clairières & racines', companion: 'Navi, la fée'
    },
    adult: {
      desc: "Sept années plus tard, le chevalier porte l'Épée de Légende et affronte un royaume tombé dans l'ombre — plus fort, plus seul, chargé d'un serment.",
      weapon: 'Épée de Légende', shield: 'Bouclier Hylien', terrain: 'Grands espaces & donjons scellés', companion: 'Epona, la jument'
    }
  };
  var ageButtons = document.querySelectorAll('.age-toggle button');
  var childImg = document.getElementById('childPortrait');
  var adultImg = document.getElementById('adultPortrait');
  ageButtons.forEach(function(btn){
    btn.addEventListener('click', function(){
      ageButtons.forEach(function(b){ b.classList.remove('active'); b.setAttribute('aria-selected','false'); });
      btn.classList.add('active'); btn.setAttribute('aria-selected','true');
      var d = ageData[btn.dataset.age];
      document.getElementById('ageDesc').textContent = d.desc;
      document.getElementById('statWeapon').textContent = d.weapon;
      document.getElementById('statShield').textContent = d.shield;
      document.getElementById('statTerrain').textContent = d.terrain;
      document.getElementById('statCompanion').textContent = d.companion;
      var isChild = btn.dataset.age === 'child';
      childImg.classList.toggle('active', isChild);
      adultImg.classList.toggle('active', !isChild);
    });
  });

  // ---- Ocarina audio (Web Audio synth, original melodies) ----
  var AudioCtx = window.AudioContext || window.webkitAudioContext;
  var actx = null;
  var soundOn = true;
  var freqs = {D4:293.66,F4:349.23,A4:440.0,B4:493.88,D5:587.33,F5:698.46};
  var noteNames = {D4:'Ré',F4:'Fa',A4:'La',B4:'Si',D5:'Ré aigu',F5:'Fa aigu'};

  function ensureCtx(){ if(!actx){ actx = new AudioCtx(); } return actx; }

  function playNote(freq, duration){
    if(!soundOn) return;
    var ctx = ensureCtx();
    var now = ctx.currentTime;
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    var filter = ctx.createBiquadFilter();
    filter.type = 'lowpass'; filter.frequency.value = 1800;
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, now);
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(.28, now + .04);
    gain.gain.exponentialRampToValueAtTime(.001, now + duration);
    osc.connect(filter); filter.connect(gain); gain.connect(ctx.destination);
    osc.start(now); osc.stop(now + duration + .05);
  }

  var caption = document.getElementById('noteCaption');
  var holes = document.querySelectorAll('.hole');
  function triggerHole(hole, duration){
    var note = hole.dataset.note;
    playNote(freqs[note], duration || .9);
    hole.classList.add('lit');
    caption.textContent = soundOn ? ('Note jouée — ' + noteNames[note]) : 'Son coupé — active-le pour entendre';
    setTimeout(function(){ hole.classList.remove('lit'); }, (duration || .9) * 1000 * .6);
  }
  holes.forEach(function(hole){
    hole.addEventListener('click', function(){ triggerHole(hole); });
    hole.addEventListener('keydown', function(e){ if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); triggerHole(hole); } });
  });

  var oceMuteBtn = document.getElementById('oceMuteBtn');
  oceMuteBtn.addEventListener('click', function(){
    soundOn = !soundOn;
    oceMuteBtn.textContent = soundOn ? '🔊 Son actif' : '🔇 Son coupé';
    oceMuteBtn.setAttribute('aria-pressed', (!soundOn).toString());
  });

  var lullaby = ['D4','F4','A4','F4','D4','B4','D5'];
  var sun = ['A4','D5','A4','D5','F5','D5','A4'];
  var epona = ['D5','B4','A4','D5','B4','A4','F4'];

  function playMelody(notes){
    if(!soundOn){ caption.textContent = 'Active le son pour écouter la mélodie'; return; }
    notes.forEach(function(note, i){
      setTimeout(function(){
        var hole = document.querySelector('.hole[data-note="'+note+'"]');
        if(hole) triggerHole(hole, .55);
      }, i * 460);
    });
  }
  document.getElementById('playLullaby').addEventListener('click', function(){ playMelody(lullaby); });
  document.getElementById('playSun').addEventListener('click', function(){ playMelody(sun); });
  document.getElementById('playEpona').addEventListener('click', function(){ playMelody(epona); });

  // ---- Site-wide background music toggle ----
  var bgm = document.getElementById('bgm');
  var musicToggle = document.getElementById('musicToggle');
  var musicLabel = document.getElementById('musicLabel');
  if(bgm){ bgm.volume = 0.55; }
  musicToggle.addEventListener('click', function(){
    if(!bgm) return;
    if(bgm.paused){
      bgm.play().then(function(){
        musicToggle.setAttribute('aria-pressed','true');
        musicLabel.textContent = 'Musique activée';
      }).catch(function(){
        musicLabel.textContent = 'Lecture impossible';
      });
    } else {
      bgm.pause();
      musicToggle.setAttribute('aria-pressed','false');
      musicLabel.textContent = 'Musique coupée';
    }
  });

  // ---- Interactive Hyrule map ----
  var mapCanvas = document.getElementById('hyruleMapCanvas');
  if(mapCanvas){
    var markersWrap = document.getElementById('hyruleMapMarkers');
    var eraButtons = document.querySelectorAll('.map-era-toggle button');
    var modal = document.getElementById('mapModal');
    var modalBackdrop = document.getElementById('mapModalBackdrop');
    var modalClose = document.getElementById('mapModalClose');
    var modalEra = document.getElementById('mapModalEra');
    var modalTitle = document.getElementById('mapModalTitle');
    var modalSummary = document.getElementById('mapModalSummary');
    var modal3d = document.getElementById('mapModal3d');
    var modal3dTabs = document.getElementById('mapModal3dTabs');
    var modal3dFrame = document.getElementById('mapModal3dFrame');
    var modal3dTodo = document.getElementById('mapModal3dTodo');
    var currentEra = 'child';
    var locations = [];

    var eraLabels = {child: 'Enfant', adult: 'Adulte'};
    var noclipLabels = {n64: 'Nintendo 64', oot3d: 'Nintendo 3DS'};

    function renderMarkers(){
      markersWrap.innerHTML = '';
      locations.forEach(function(loc){
        var btn = document.createElement('button');
        btn.className = 'map-marker';
        btn.style.left = loc.x + '%';
        btn.style.top = loc.y + '%';
        btn.setAttribute('aria-label', loc.name);
        if(loc.era.indexOf(currentEra) === -1){ btn.hidden = true; }
        var label = document.createElement('span');
        label.className = 'map-marker-label';
        label.textContent = loc.name;
        btn.appendChild(label);
        btn.addEventListener('click', function(){ openLocation(loc); });
        markersWrap.appendChild(btn);
      });
    }

    function loadNoclip(url){
      modal3dFrame.innerHTML = '';
      var iframe = document.createElement('iframe');
      iframe.src = url;
      iframe.allow = 'fullscreen; xr-spatial-tracking';
      iframe.loading = 'lazy';
      modal3dFrame.appendChild(iframe);
    }

    function openLocation(loc){
      modalEra.textContent = loc.era.map(function(e){ return eraLabels[e]; }).join(' · ');
      modalTitle.textContent = loc.name;
      modalSummary.textContent = loc.summary;

      var available = Object.keys(loc.noclip || {}).filter(function(k){ return loc.noclip[k]; });
      modal3dTabs.innerHTML = '';
      if(available.length){
        modal3d.hidden = false;
        modal3dTodo.hidden = true;
        available.forEach(function(key, i){
          var tab = document.createElement('button');
          tab.type = 'button';
          tab.textContent = noclipLabels[key] || key;
          tab.className = i === 0 ? 'active' : '';
          tab.addEventListener('click', function(){
            Array.from(modal3dTabs.children).forEach(function(t){ t.classList.remove('active'); });
            tab.classList.add('active');
            loadNoclip(loc.noclip[key]);
          });
          modal3dTabs.appendChild(tab);
        });
        loadNoclip(loc.noclip[available[0]]);
      } else {
        modal3d.hidden = true;
        modal3dFrame.innerHTML = '';
        modal3dTodo.hidden = false;
      }

      modal.hidden = false;
      modalClose.focus();
      document.body.style.overflow = 'hidden';
    }

    function closeModal(){
      modal.hidden = true;
      modal3dFrame.innerHTML = ''; // stop any running noclip WebGL context
      document.body.style.overflow = '';
    }
    modalBackdrop.addEventListener('click', closeModal);
    modalClose.addEventListener('click', closeModal);
    document.addEventListener('keydown', function(e){
      if(e.key === 'Escape' && !modal.hidden) closeModal();
    });

    eraButtons.forEach(function(btn){
      btn.addEventListener('click', function(){
        eraButtons.forEach(function(b){ b.classList.remove('active'); b.setAttribute('aria-selected','false'); });
        btn.classList.add('active'); btn.setAttribute('aria-selected','true');
        currentEra = btn.dataset.mapEra;
        renderMarkers();
      });
    });

    fetch('data/locations.json')
      .then(function(r){ return r.json(); })
      .then(function(data){
        locations = data.locations || [];
        renderMarkers();
      })
      .catch(function(){
        markersWrap.innerHTML = '<p style="color:#d8d0b4; padding:20px; position:relative;">Carte indisponible pour le moment.</p>';
      });
  }
})();
