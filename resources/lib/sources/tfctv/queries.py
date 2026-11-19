# -*- coding: utf-8 -*-

"""
The GraphQL queries of the website, as the website sends them (the calls are in graphql.py)
"""

SEARCH = """query Search($query: String, $skus: [String!]) {
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
    }"""

WATCHLIST = """query Watchlist($skus: [String!]) {
    watchlist(skus: $skus) {
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
            genres
            releaseDate
            cast
            rating
            tvShowDetails {
                totalSeasons
                tvShowType
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
        }
        totalItems
        pageSize
        currentPage
        totalPages
        hasNextPage
    }
}"""

APP_LAUNCH_DETAILS = """query AppLaunchDetails {
            appLaunchDetails
        }"""

COLLECTION = """query Collection($collectionId: ID, $skus: [String!]) {
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
}"""

TV_SHOW_EPISODES = """
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
        """

ASSET = """
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
}"""
