<?php
require_once __DIR__ . '/specialChars.php';

$fname = $argv[1];

$list = file( $fname );
$outname = isset($argv[2]) ? $argv[2] : $fname.".out";
$out = fopen( $outname, 'w');
$year = '';
$title = '';
$class = '';
$lastFirst = false;
$athleteCount = 0;
foreach( $list as $line ) {
	$line = trim($line);
    if (!empty($line)) {
 		switch( $line[0] ) {
			case 'y':
				$year = substr($line, 2);
				break;
			case 't':
				$title = substr($line,2);
				break;
			case 'C':
				echo "===> POSSIBLE ERROR - upper case C: ?\n$line\n\n";
			case 'c':
				$class = substr($line,2);
				break;
			case 'l':		// last first but with no comma
				$lastFirst = substr($line,2,1) == '1';
				break;
			case '-':
				fwrite( $out, "----\n");
				$class = '';
				break;
			default:
				$athleteCount++;
				formatLine( $out, cleanUTF($line), $year, $title, $class, $lastFirst );
		}
	}
}
echo "ATHLETES_COUNT=$athleteCount\n";
exit();

function cleanUTF( $line ) {
	$str = SpecialChars::replace($line);
	$flag = $str != htmlentities($str, ENT_COMPAT | ENT_IGNORE, "UTF-8") ? ' <<<<<<' : '';
	if( $str != $line ) {
		echo "$line -> $str$flag\n";
	}
	if ($flag != '') {
		echo PHP_EOL, "$line $flag", PHP_EOL;
		echo bin2hex($str), PHP_EOL, PHP_EOL;
	}
	return $str;
}

function formatLine( $out, $line, $year, $title, $class, $lastFirst ) {
	$asian = $line[0] == '*' || $line[0] == '@';
	if( $asian ) $line[0] = '0';
	$pos = intval( $line );
//	if( $pos == 16 ) $pos = 98;
	$array = preg_split( "/[\s\.]/", $line, 2, PREG_SPLIT_NO_EMPTY );
	if( count($array) > 1 ) {
		list( $line, $country ) = extractCountry(trim($array[1]));
		if( $country == 'c=CN' || $country == 'c=TW' ) $asian = true;
	} else {
	  $country = '';
	}
	list( $name, $note ) = formatName($line, $asian, $lastFirst, $array);
	$rank = $class == '' ? $pos : "$class-$pos";
	fwrite( $out, "$name; $year; $title; $rank;$country$note\n" );
}

function getCountryCode( $country ) {

static $countryCode3 = array(
	'ARG'=>'AR',
	'AUS'=>'AU',
	'AUT'=>'AT',
	'BEL'=>'BE',
	'BIH'=>'BA',
	'BOL'=>'BO',
	'BRA'=>'BR',
	'CAN'=>'CA',
	'CHE'=>'CH',
	'CHN'=>'CN',
	'CZE'=>'CZ',
	'DEU'=>'DL',
	'ESP'=>'ES',
	'EST'=>'EE',
	'FRA'=>'FR',
	'GBR'=>'UK',
	'GER'=>'DE',
	'GRE'=>'GR',
	'HOL'=>'NL',
	'HUN'=>'HU',
	'IND'=>'IN',
	'IRL'=>'IE',
	'IRN'=>'IR',
	'ISR'=>'IL',
	'ITA'=>'IT',
	'KAZ'=>'KZ',
	'KGZ'=>'KY',
	'KOR'=>'KO',
	'KUW'=>'KW',
	'LAT'=>'LV',
	'LIT'=>'LT',
	'LTU'=>'LT',
	'LUX'=>'LU',
	'LVA'=>'LV',
	'MEX'=>'MX',
	'MYS'=>'MY',
	'NIR'=>'UK',
	'NLD'=>'NL',
	'NED'=>'NL',
	'NOR'=>'NO',
	'NZL'=>'NZ',
	'PHL'=>'PH',
	'POL'=>'PL',
	'ROM'=>'RO',
	'RSA'=>'ZA',
	'RUS'=>'RU',
	'SCO'=>'UK',
	'SPA'=>'ES',
	'SUI'=>'CH',
	'SWE'=>'SE',
	'SVK'=>'SK',
	'TRNC'=>'CY',
	'TUR'=>'TR',
	'UKR'=>'UA',
	'UZB'=>'UZ',
	'WAL'=>'UK'
);

static $countryCode = array( 
		"Afghanistan"=>"AF",
		"Albania"=>"AL",
		"Algeria"=>"DZ",
		"Anguilla"=>"AI",
		"Antigua and Barbuda"=>"AG",
		"Argentina"=>"AR",
		"Aruba"=>"AW",
		"Australia"=>"AU",
		"Austria"=>"AT",
		"Azerbaijan"=>"AZ",
		"Bahamas"=>"BS",
		"Bahrain"=>"BH",
		"Bangladesh"=>"BD",
		"Barbados"=>"BB",
		"Belarus"=>"BY",
		"Belgium"=>"BE",
		"Belize"=>"BZ",
		"Bermuda"=>"BM",
		"Bhutan"=>"BT",
		"Bolivia"=>"BO",
		"Brasil"=>"BR",
		"Brazil"=>"BR",
		"Brunei"=>"BN",
		"Bulgaria"=>"BG",
		"Canada"=>"CA",
		"Chile"=>"CL",
		"China"=>"CN",
		"Chinese Tapei"=>"TW",
		"Costa Rica"=>"CR",
		"Columbia"=>"CO",
		"Colombia"=>"CO",
		"Croatia"=>"HR",
		"Cuba"=>"CU",
		"Cyprus"=>"CY",
		"Czechia"=>"CZ",
		"Czech Republic"=>"CZ",
		"Czechoslovakia"=>"CS",
		"Denmark"=>"DK",
		"Dominica"=>"DM",
		"Dominican Republic"=>"DO",
		"Ecuador"=>"EC",
		"Egypt"=>"EG",
		"El Salvador"=>"SV",
		"England"=>"EN",
		"Estonia"=>"EE",
		"Finland"=>"FI",
		"France"=>"FR",
		"Germany"=>"DE",
		"Georgia"=>"GE",
		"Greece"=>"GR",
		"Grenada"=>"GD",
		"Guadeloupe"=>"GP",
		"Guam"=>"GU",
		"Guatemala"=>"GT",
		"Guyana"=>"GY",
		"Haiti"=>"HT",
		"Holland"=>"HO",
		"Hong Kong"=>"HK",
		"Hungary"=>"HU",
		"Iceland"=>"IS",
		"India"=>"IN",
		"Indonesia"=>"ID",
		"Iran"=>"IR",
		"Iraq"=>"IQ",
		"Ireland"=>"IE",
		"Israel"=>"IL",
		"Italy"=>"IT",
		"Jamaica"=>"JM",
		"Japan"=>"JP",
		"Jordan"=>"JO",
		"Kazakhstan"=>"KZ",
		"Korea"=>"KO",
		"Kuwait"=>"KW",
		"Latvia"=>"LV",
		"Lebanon"=>"LB",
		"Libya"=>"LY",
		"Lithuania"=>"LT",
		"Luxembourg"=>"LX",
		"Macau"=>"MO",
		"Macedonia"=>"MK",
		"Malaysia"=>"MY",
		"Malta"=>"MT",
		"Martinique"=>"MQ",
		"Mauritius"=>"MU",
		"Mexico"=>"MX",
		"Moldovia"=>"MD",
		"Mongolia"=>"MN",
		"Morocco"=>"MA",
		"Maldives"=>"MV",
		"Myanmar"=>"MM",
		"Nepal"=>"NP",
		"Netherlands"=>"NL",
		"Netherlands Antilles"=>"AN",
		"New Zealand"=>"NZ",
		"Nicaragua"=>"NI",
		"Nigeria"=>"NG",
		"Norway"=>"NO",
		"Oman"=>"OM",
		"Pakistan"=>"PK",
		"Palestine"=>"PS",
		"Panama"=>"PA",
		"Paraguay"=>"PY",
		"Peru"=>"PE",
		"Philippines"=>"PH",
		"Poland"=>"PL",
		"Poland"=>"PO",
		"Portugal"=>"PT",
		"Puerto Rico"=>"PR",
		"Qatar"=>"QA",
		"Reunion Island"=>"RE",
		"Romania"=>"RO",
		"Russia"=>"RU",
		"Saudi Arabia"=>"SA",
		"Saudia Arabia"=>"SA",
		"Scotland"=>"SC",
		"Serbia"=>"SB",
		"Serbia &amp; Montenegro"=>"SM",
		"Seychelles"=>"sc",
		"Singapore"=>"SG",
		"Slovakia"=>"SK",
		"Slovenia"=>"SL",
		"South Africa"=>"ZA",
		"Soviet Union"=>"SU",
		"Spain"=>"ES",
		"Sri Lanka"=>"LK",
		"St Lucia"=>"LC",
		"St Vincent"=>"VC",
		"Sweden"=>"SE",
		"Switzerland"=>"CH",
		"Syria"=>"SY",
		"Taiwan"=>"TW",
		"Trinidad and Tobego"=>"TT",
		"Trinidad & Tobago"=>"TT",
		"Thailand"=>"TH",
		"Turkey"=>"TR",
		"Turks and Caicos Islands"=>"TC",
		"Ukraine"=>"UA",
		"United Arab Emirates"=>"AE",
		"United Kingdom"=>"UK",
		"United States"=>"US",
		"USA"=>"US",
		"Uruguay"=>"UY",
		"Uzbekistan"=>"UZ",
		"Venezuela"=>"VE",
		"Vietnam"=>"VN",
		"Wales"=>"WA",
		"West Germany"=>"WG",
		"Yugoslavia"=>"YU"
);

	$up = strtoupper($country);
	if( array_key_exists( $up, $countryCode3 ) ) {
		return $countryCode3[$up];
	} else if( array_key_exists( $country, $countryCode ) ) {
		return $countryCode[$country];
	} else if( strpos($country, ',') ) { 
		return 'US';
	} else {
		$uc = ucwords(strtolower($country));
		return array_key_exists( $uc, $countryCode ) ? $countryCode[$uc] : $country;
	}
}

function extractCountry( $line ) {				// TODO: error if last name is 3 upper case characters
//	$last_3 = substr($line, -3);
//	if( $last_3 == strtoupper($last_3) && substr($line,-4,1) == ' ') {
//		$line[strlen($line)-4] = ';';
//	}

	list( $line, $country, $rest ) = explode( ';', $line.";;", 3 );
	$country = trim($country);
	if( empty($country) ) {
		preg_match( "/\(([^)]*)\)/", $line, $matches );
		if( count($matches) == 2 ) {
			$line = trim(str_replace( $matches[0], '', $line ));
			$country = $matches[1];
		}
	}
	if( strlen($country) > 2 ) {
		$country = getCountryCode( $country );
	} else {
		$country = strtoupper( $country );
		if ($country == "GB" ) $country = "UK";
	}
	$alert = strlen($country) > 2 ? " ******* " : "";
	if( !empty($country) ) $country = " c=".$country.";".$alert;
	return array($line, $country);
}

function formatName($line, $asian, $lastFirst, $diag=null) {
	$orig_line = $line;
	$note = '';
	$line = titleCase( $line );
	$exact = strpos( $line, ', ' ) !== false;
	if( $exact ) {
		$name = $line;
	} else {
		$fields = explode(' ', str_replace( array(',','.'), '', $line ) );
		$count = count($fields);
		if( $asian ) {
			$name = implode( ' ', $fields );
		} else if( $count == 2 ) {
			if( $lastFirst ) {
				$name = $fields[0].', '.$fields[1];
			} else {
				$name = $fields[1].', '.$fields[0];
			}
		} else {
			$jr = strtolower( $fields[$count-1] ) == 'jr';
			if( $jr ) {
				$count--;
				$fields[$count] = '';
			}
			if( empty($fields)) {
				echo "error ----->$orig_line {$diag[0]} {$diag[1]}\n";
				return [ '', '' ];
			} else if( count($fields) < 2 ) {
				return [ $fields[0], '<<<<'];
			} else if( strlen($fields[1]) == 1 || $count == 4) {
				$firstName = trim(join(' ', array_slice( $fields, 0, 2 ) ));
				$lastName = trim(join(' ', array_slice( $fields, 2 ) ));
			} else if( $lastFirst ) {
				$lastName = $fields[0];
				$firstName = trim(join(' ', array_slice( $fields, 1 ) ));
			} else {
				$firstName = $fields[0];
				$lastName = trim(join(' ', array_slice( $fields, 1 ) ));
			}
			$name = $lastName.", ".$firstName;
			if( $jr ) $name .= ' Jr';
			$note = " <<<<";
		}
	}
	return [$name, $note];
}

function titleCase( $line ) {
	$line = ucwords(strtolower($line));
	$delimiters = array( "O'", "Mc", "-" );
	foreach( $delimiters as $delim ) {
		$i = strpos( $line, $delim );
		$next = $i + strlen( $delim );
		if( $i !== false && $next < strlen( $line ) ) {
			$line[$next] = strtoupper( $line[$next] );
		}
	}
	return $line;
}
