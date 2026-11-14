# -*- coding: utf-8 -*-

"""
Calls of the website GraphQL API (no database access)
"""


from resources import config
from resources.lib.libraries import control
from .api import callGraphQLApi
from .user import getCountryCode, getServiceIds

logger = control.logger

def searchCatalog(query):
    """Search catalog"""
    logger.logInfo('called function')
    response = callGraphQLApi(
"""query Search($query: String, $skus: [String!]) {
    search(query: $query, skus: $skus) {
        id
        rails {
        id
        railType
        title
        assets {
            items {
            id
            assetType
            title
            shortDescription
            images {
                landscape
                landscapeHero
                portrait
                portraitHero
                title
                square
            }
            isPlayable
            duration
            durationInSeconds
            labels {
                id
                position
                url
            }
            trailerUrls {
                dash {
                url
                }
            }
            genres
            releaseDate
            earlyAccessDate
            cast
            contentDescriptors
            contentOwner
            durationInMs
            directors
            languages
            originalLanguage
            rating
            videoQuality {
                id
                label
            }
            audioQuality {
                id
                label
            }
            subtitleLanguages
            subHeader
            subHeaders
            showInfo {
                id
                title
                tvShowType
                images {
                landscape
                landscapeHero
                portrait
                portraitHero
                title
                square
                }
            }
            tvShowDetails {
                totalSeasons
                tvShowType
                defaultEpisode {
                id
                title
                subHeader
                onAirDate
                }
            }
            monetization {
                type
                logoUrl
                hasSkuAccess
            }
            seasons {
                id
                title
                count
                filter {
                year
                month
                seasonId
                }
            }
            promotionalTag {
                iconUrl
                text
            }
            continueWatching {
                playbackPosition
                audioLang
                subtitleLang
                resolution
                bitrate
            }
            videoOrientation
            }
            currentPage
            hasNextPage
            hasPreviousPage
            pageSize
            totalItems
            totalPages
        }
        dynamicDataQuery
        isDynamicData
        preAggregated
        railSubType
        sourceType
        }
    }
    }""",
        {
            'query': query,
            'skus': getServiceIds(),
            'apiCode':'GSE'
        },
        useCache=False
    )
    return response


def getAppLaunchDetails():
    """Get app launch details from website"""
    logger.logInfo('called function')
    data = callGraphQLApi(
        """query AppLaunchDetails {
            appLaunchDetails
        }""",
        {},
        [
            ('Referer', config.websiteSecuredUrl+'/'),
            ('Origin', config.websiteSecuredUrl),
            ('x-device-platform', 'web'),
            ('X-Device-SubPlatform', 'firefox'),
            ('X-IW-UserAgent', 'Name=iWant; Version=1.0.0; Platform=Web; OSVersion=14.0.0 Model=Chrome; BuildType=debug Environment=development'),
            ('x-country-code', getCountryCode()),
            ('Sec-GPC', '1'),
            ('Sec-Fetch-Dest', 'empty'),
            ('Sec-Fetch-Mode', 'cors'),
            ('Sec-Fetch-Site', 'same-site'),
            ('Priority', 'u=4'),
            ('TE', 'trailers')
        ],
        useCache=False
    )
    if data and 'appLaunchDetails' in data:
        logger.logDebug(data['appLaunchDetails'])
        return data['appLaunchDetails']
    return {}

def getCollection(id):
    """Get collection"""
    logger.logInfo('called function with param (%s)' % id)
    response = callGraphQLApi(
"""query Collection($collectionId: ID, $skus: [String!]) {
      collection(id: $collectionId, skus: $skus) {
        id
    bannerAds {
          ads {
            adUnitId
        position
        adUnitSize {
              width
          height
        }
        adParams
      }
    }
    rails {
          id
      railType
      title
      images {
            titleUrl
        backgroundOverlayUrl
        sponsoredSectionBgImgUrl
        sponsoredBackdropImgUrl
      }
      assets {
            items {
              id
          assetType
          title
          shortDescription
          images {
                landscape
            landscapeHero
            portrait
            portraitHero
            title
            square
          }
          isPlayable
          duration
          durationInSeconds
          labels {
                id
            position
            url
          }
          trailerUrls {
                dash {
                  url
            }
          }
          genres
          releaseDate
          earlyAccessDate
          cast
          contentCategoryType
          contentDescriptors
          contentOwner
          durationInMs
          directors
          languages
          originalLanguage
          rating
          videoQuality {
                id
            label
          }
          audioQuality {
                id
            label
          }
          subtitleLanguages
          subHeader
          subHeaders
          showInfo {
                id
            title
            tvShowType
            images {
                  landscape
              landscapeHero
              portrait
              portraitHero
              title
              square
            }
          }
          tvShowDetails {
                totalSeasons
            tvShowType
            defaultEpisode {
                  id
              title
              subHeader
              onAirDate
            }
          }
          monetization {
                type
            logoUrl
            hasSkuAccess
          }
          seasons {
                id
            title
            count
            filter {
                  year
              month
              seasonId
            }
          }
          promotionalTag {
                iconUrl
            text
          }
          continueWatching {
                playbackPosition
            audioLang
            subtitleLang
            resolution
            bitrate
          }
          videoOrientation
        }
        currentPage
        hasNextPage
        hasPreviousPage
        pageSize
        totalItems
        totalPages
      }
      dynamicDataQuery
      isDynamicData
      preAggregated
      railSubType
      sourceType
    }
  }
}""",
        variables={
            'collectionId': id,
            'skus': getServiceIds()
        },
        useCache=False
    )
    if response and 'collection' in response:
        return response['collection']
    return {}

def getTVShowEpisodes(id, page=1, itemsPerPage=500, year=None, month=None, seasonId=None):
    """Get TV show details"""
    logger.logInfo('called function with param (%s)' % id)
    response = callGraphQLApi("""
query TvShowEpisodes($tvShowEpisodesId: ID, $filters: TvShowEpisodesFilterInput, $skus: [String!]) {
  tvShowEpisodes(id: $tvShowEpisodesId, filters: $filters, skus: $skus) {
    items {
      id
      assetType
      title
      shortDescription
      images {
        landscape
        landscapeHero
        portrait
        portraitHero
        title
        square
      }
      isPlayable
      duration
      durationInSeconds
      labels {
        id
        position
        url
      }
      trailerUrls {
        dash {
          url
        }
      }
      genres
      releaseDate
      earlyAccessDate
      cast
      contentDescriptors
      contentOwner
      durationInMs
      directors
      languages
      originalLanguage
      rating
      videoQuality {
        id
        label
      }
      audioQuality {
        id
        label
      }
      subtitleLanguages
      subHeader
      subHeaders
      showInfo {
        id
        title
        tvShowType
        images {
          landscape
          landscapeHero
          portrait
          portraitHero
          title
          square
        }
      }
      tvShowDetails {
        totalSeasons
        tvShowType
        defaultEpisode {
          id
          title
          subHeader
          onAirDate
        }
      }
      monetization {
        type
        logoUrl
        hasSkuAccess
      }
      seasons {
        id
        title
        count
        filter {
          year
          month
          seasonId
        }
      }
      promotionalTag {
        iconUrl
        text
      }
      continueWatching {
        playbackPosition
        audioLang
        subtitleLang
        resolution
        bitrate
      }
      videoOrientation
    }
    totalItems
    pageSize
    currentPage
    totalPages
    hasNextPage
    hasPreviousPage
  }
}
        """,
        variables={
            'tvShowEpisodesId': id,
            'filters':{
                'year': year,
                'month': month,
                'seasonId': seasonId,
                'pageNumber': page,
                'pageSize': itemsPerPage
            },
            'skus': getServiceIds()
        },
        useCache=False
    )
    # the API answers with a null tvShowEpisodes (and an error) when the filters match nothing
    return (response.get('tvShowEpisodes') if response else None) or {}

def getAsset(id):
    """Get asset details"""
    logger.logInfo('called function with param (%s)' % id)
    response = callGraphQLApi("""
query Asset($assetId: ID, $skus: [String!]) {
  asset(id: $assetId, skus: $skus) {
    id
    assetType
    title
    shortDescription
    images {
      landscape
      landscapeHero
      portrait
      portraitHero
      title
      square
    }
    isPlayable
    duration
    durationInSeconds
    labels {
      id
      position
      url
    }
    trailerUrls {
      dash {
        url
      }
    }
    genres
    releaseDate
    earlyAccessDate
    cast
    contentDescriptors
    contentOwner
    durationInMs
    directors
    languages
    originalLanguage
    rating
    videoQuality {
      id
      label
    }
    audioQuality {
      id
      label
    }
    subtitleLanguages
    subHeader
    subHeaders
    showInfo {
      id
      title
      tvShowType
      seasonNumber
      episodeNumber
      images {
        landscape
        landscapeHero
        portrait
        portraitHero
        title
        square
      }
    }
    tvShowDetails {
      totalSeasons
      tvShowType
      defaultEpisode {
        id
        title
        subHeader
        onAirDate
      }
    }
    monetization {
      type
      logoUrl
      hasSkuAccess
    }
    seasons {
      id
      title
      count
      filter {
        year
        month
        seasonId
      }
    }
    promotionalTag {
      iconUrl
      text
    }
    continueWatching {
      playbackPosition
      audioLang
      subtitleLang
      resolution
      bitrate
    }
    slugUrl
    videoOrientation
  }
}""",
        variables={
            'assetId': id,
            'skus': getServiceIds()
        },
        useCache=False
    )

    return response.get('asset', {}) if response else {}
