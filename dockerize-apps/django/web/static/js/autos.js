jQuery(function() {
    var availableTags = [
        "Paris",
        "Marseille",
        "Lyon",
        "Toulouse",
        "Nice",
        "Nantes",
        "Montpellier",
        "Strasbourg",
        "Bordeaux",
        "Lille",
        "Rennes",
        "Reims",
        "Saint-Étienne",
        "Toulon",
        "Le Havre",
        "Grenoble",
        "Dijon",
        "Angers",
        "Nîmes",
        "Saint-Denis (La Réunion)",
        "Villeurbanne",
        "Clermont-Ferrand",
        "Le Mans",
        "Aix-en-Provence",
        "Brest",
        "Tours",
        "Amiens",
        "Limoges",
        "Annecy",
        "Perpignan",
        "Boulogne-Billancourt",
        "Orléans",
        "Metz",
        "Besançon",
        "Saint-Denis",
        "Argenteuil",
        "Rouen",
        "Montreuil",
        "Mulhouse",
        "Caen",
        "Saint-Paul",
        "Nancy",
        "Tourcoing",
        "Roubaix",
        "Nanterre",
        "Vitry-sur-Seine",
        "Avignon",
        "Créteil",
        "Poitiers",
        "Dunkerque",
        "Aubervilliers",
        "Versailles",
        "Aulnay-sous-Bois",
        "Asnières-sur-Seine",
        "Colombes",
        "Saint-Pierre",
        "Courbevoie",
        "Fort-de-France",
        "Cherbourg-en-Cotentin",
        "Le Tampon",
        "Rueil-Malmaison",
        "Champigny-sur-Marne",
        "Béziers",
        "Pau",
        "La Rochelle",
        "Saint-Maur-des-Fossés",
        "Calais",
        "Cannes",
        "Antibes",
        "Drancy",
        "Ajaccio",
        "Mérignac",
        "Saint-Nazaire",
        "Colmar",
        "Issy-les-Moulineaux"
    ];
    jQuery("#lname").autocomplete({
      source: availableTags
    });
  });