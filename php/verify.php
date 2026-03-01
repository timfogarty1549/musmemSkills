<?php

/**
 * last - find similar sounding last names with same first name
 * first - find same last names with similar sounding first names
 * order - find 3+ names mismatch, covers first <---> last
 * anagram - 
 * country - find athlete with multiple country codes
 * duplicate - find name appearing twice in same contest, same division
 * test - look for records with not enough fields
 */


if (count($argv) < 2 || $argv[1][0] == '-' ) {
  echo "\nphp -f verify.php [format,last,first,country,anagram,order]\n\n";
  exit;
}

$case = $argv[1];
switch( $case ) {
	case 'format':
		testFormat( 'bb_male.dat' );
		testFormat( 'bb_female.dat' );
		break;
	case 'last':
		findSimilarNames( 'bb_male.dat', false );
		findSimilarNames( 'bb_female.dat', false );
		break;
	case 'first':
		findSimilarNames( 'bb_male.dat', true );
		findSimilarNames( 'bb_female.dat', true );
		break;
	case 'country':
		findMultiCountry( 'bb_male.dat' );
		findMultiCountry( 'bb_female.dat' );
		break;
	case 'anagram':
		findAnagram( 'bb_male.dat' );
		findAnagram( 'bb_female.dat' );
		break;
	case 'order':
	default:
		findReversedNames( 'bb_male.dat' );
		findReversedNames( 'bb_female.dat' );
}
exit;

function removeInternal( $name ) {
	return str_replace(array(':','--','^','~',"'","''",'@','/','.','_',), '', 
		str_replace( "s*", "ss", $name ) );
}

class Athlete {
	public $athlete;
	public $y0;
	public $y1;
	public $count;
	
	public function __construct( $athlete, $year ) {
		$this->athlete = $athlete;
		$this->y0 = $year;
		$this->y1 = $year;
		$this->count = 1;
	}
	
	public function incr( $year ) {
		$this->y1 = $year;
		$this->count++;
	}
	
	public function out() {
		echo "{$this->athlete}, {$this->count}, {$this->y0}, {$this->y1}\n";
	}
}

function testFormat( $file_name ) {
	$file = file ( $file_name );
	$num = 0;
	foreach ( $file as $line ) {
		$num = substr_count( $line, ';' );
		if( $num < 4 ) echo $line;
	}
}

function findSimilarNames( $file_name, $flag ) {
	$list = array ();
	$prev = '';
	$file = file ( $file_name );
	$num = 0;
	foreach ( $file as $line ) {
		list ( $athlete, $year, $rest ) = explode ( ';', $line, 3 );
		if( $athlete != $prev ) {
			$prev = $athlete;
			$obj = new Athlete( $athlete, $year );
			$name = preg_replace( '/[^\da-z,]/i', '', $athlete );
			if( $flag ) list( $first, $last ) = explode( ',', $name );
			else list( $last, $first ) = explode( ',', $name );
			if( !empty($last) ) {
				$sx = soundex( $last );
				if( !array_key_exists( $sx, $list ) ) {
					$list[$sx] = array();
				}
				if( !array_key_exists( $first, $list[$sx] ) ) {
					$list[$sx][$first] = array();
				}
				$list[$sx][$first][] = $obj;
			}
		} else {
			$obj->incr( $year );
		}
	}
	ksort( $list );
	foreach( $list as $sub ) {
		if( count($sub) > 1 ) {
			foreach( $sub as $item ) {
				if( count($item) > 1 && rangeOverlaps( $item ) ) {
					$num++;
					foreach( $item as $o ) {
						$o->out();
					}
					echo "\n";
				}
			}
		}
	}
	echo "num items $num\n--------------\n";
}

function rangeOverlaps( $list ) {
	if( count($list) > 2 ) return false;
	if( $list[0]->y0 < $list[1]->y0 ) {
		$a = $list[0];
		$b = $list[1];
	} else {
		$a = $list[1];
		$b = $list[0];
	}
	return $b->y1 == 2015 && $a->y1 >= $b->y0;
}

function findReversedNames( $file_name ) {
	$list = array ();
	$prev = '';
	$file = file ( $file_name );
	$num = 0;
	foreach ( $file as $line ) {
		list ( $athlete, $rest ) = explode ( ';', $line, 2 );
		if( $athlete != $prev ) {
			$prev = $athlete;
			$a = removeInternal( str_replace( '-', ' ', $athlete ) );
			$names = explode( ' ', $a );
			sort( $names );
			$merge = strtolower( implode( '', $names ) );
			if( !array_key_exists( $merge, $list ) ) {
				$list[$merge] = array();
			}
			$list[$merge][] = $athlete;
		}
	}
	foreach( $list as $sub ) {
		if( count($sub) > 1 ) {
			$num++;
			foreach( $sub as $item ) {
				echo $item."\n";
			}
			echo "\n";
		}
	}
	echo "num items $num\n----------------\n";
}

function extractCountry( $country ) {
	$c = substr( $country, 2, -1 );
	if( $c == 'SC' ) $c = 'UK';
	else if( $c == 'EN' ) $c = 'UK';
	else if( $c == 'WA' ) $c = 'UK';
	else if( $c == 'RE' ) $c = 'FR';
	else if( $c == 'GP' ) $c = 'FR';
	else if( $c == 'MF' ) $c = 'FR';
	else if( $c == 'MU' ) $c = 'FR';
	else if( $c == 'WG' ) $c = 'DE';
	else if( $c == 'YU' ) $c = 'SB';
	else if( $c == 'SM' ) $c = 'SB';
	else if( $c == 'ME' ) $c = 'SB';
	else if( $c == 'BA' ) $c = 'SB';
	else if( $c == 'AN' ) $c = 'CW';
	else if( $c == 'AW' ) $c = 'CW';
	else if( $c == 'BQ' ) $c = 'CW';
	else if( $c == 'CS' ) $c = 'CZ';
	else if( $c == 'PR' ) $c = 'US';
	return $c;
}

function findMultiCountry( $file_name ) {
	$list = array ();
	$prev = '';
	$file = file ( $file_name );
	$num = 0;
	foreach ( $file as $line ) {
		list ( $athlete, $rest ) = explode ( ';', $line, 2 );
		if( $athlete != $prev ) {
			$prev = $athlete;
			$list[$athlete] = array();
		}
		if( preg_match( "/c=(.*?);/i", $rest, $match ) ) {
			if( strpos( $rest, '-99' ) === false ) {
				$key = extractCountry( $match[0] );
				if( !array_key_exists( $key, $list[$athlete] ) ) {
					$list[$athlete][$key] = 1;
				}
			}
		}
	}
	foreach( $list as $athlete=>$array ) {
		if( count($array) > 1 ) {
			$countries = implode( " | ", array_keys($array) );
			echo "$athlete | $countries\n";
			$num++;
		}
	}
	echo "num items $num\n----------------\n";
}



function findAnagram( $file_name ) {
	$list = array ();
	$prev = '';
	$file = file ( $file_name );
	$num = 0;
	foreach ( $file as $line ) {
		list ( $athlete, $rest ) = explode ( ';', $line, 2 );
		if( $athlete != $prev ) {
			$prev = $athlete;
			$name = removeInternal( str_replace( [' ','-'], '', $athlete ) );
			$letters = str_split(strtolower($name));
			sort($letters);
			$merge = implode( '', $letters );
			if( !array_key_exists( $merge, $list ) ) {
				$list[$merge] = array();
			}
			$list[$merge][] = $athlete;
		}
	}
	foreach( $list as $sub ) {
		if( count($sub) > 1 ) {
			$num++;
			foreach( $sub as $item ) {
				echo $item."\n";
			}
			echo "\n";
		}
	}
	echo "num items $num\n----------------\n";
}
